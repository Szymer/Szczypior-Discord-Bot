"""Szczypior Discord Bot - Klient Gemini AI."""

import json
import os
from io import BytesIO
from typing import Any, Dict, Optional

from google import genai
from google.genai import types as genai_types
import requests
from dotenv import load_dotenv
from PIL import Image, ImageStat

from .base_client import BaseLLMClient
from .rate_limiter import ModelRateLimiter

# Wczytaj zmienne środowiskowe
load_dotenv()


class GeminiClient(BaseLLMClient):
    """Klient do komunikacji z Google Gemini AI."""



    _DEFAULT_MODEL = "models/gemini-3.1-flash-lite-preview"

    @staticmethod
    def _parse_model_list(raw: str) -> list[str]:
        """Parsuje listę modeli z formatu '[model1, model2]' lub 'model1, model2'."""
        raw = raw.strip()
        if raw.startswith("[") and raw.endswith("]"):
            raw = raw[1:-1]
        return [item.strip() for item in raw.split(",") if item.strip()]

    def __init__(
        self,
        model_name: Optional[str] = None,
        generation_params: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        """
        Inicjalizuje klienta Gemini.

        Args:
            model_name: Nazwa modelu Gemini do użycia.
            generation_params: Parametry generowania (temperature, max_tokens, itp.).
            **kwargs: Dodatkowe argumenty.
        """
        super().__init__(model_name, **kwargs)

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("Nie znaleziono klucza GEMINI_API_KEY w zmiennych środowiskowych.")

        # Nowy SDK używa centralnego klienta zamiast obiektów GenerativeModel.
        # Preview modele (np. gemini-3.1) wymagają v1beta endpoint.
        self.client = genai.Client(
            api_key=api_key,
            http_options={"api_version": "v1beta"},
        )

        # Ustaw domyślny model jeśli nie podano
        if not self.model_name:
            google_models_raw = os.getenv("GOOGLE_MODELS", "").strip()
            if google_models_raw:
                models = self._parse_model_list(google_models_raw)
                self.model_name = models[0] if models else self._DEFAULT_MODEL
            else:
                self.model_name = self._DEFAULT_MODEL

        self.model_name = self._normalize_model_name(self.model_name)

        # Zapisz parametry generowania
        self.generation_params = generation_params or {}

        # Rate limiter — czyta GOOGLE_RPM z env
        self._rate_limiter = ModelRateLimiter.from_env()

    def _fallback_models(self) -> list[str]:
        """Zwraca listę modeli fallback używanych gdy bazowy model jest niedostępny."""
        google_models_raw = os.getenv("GOOGLE_MODELS", "").strip()
        if google_models_raw:
            all_models = [
                self._normalize_model_name(m)
                for m in self._parse_model_list(google_models_raw)
            ]
            # Opuść pierwszy model (primary) — reszta to fallbacki
            return [m for m in all_models[1:] if m != self.model_name]

        env_raw = os.getenv("GEMINI_FALLBACK_MODELS", "").strip()
        if env_raw:
            return [self._normalize_model_name(item) for item in env_raw.split(",") if item.strip()]

        return [
            "models/gemini-2.0-flash",
            "models/gemini-1.5-flash",
        ]

    @staticmethod
    def _should_try_fallback(exc: Exception) -> bool:
        """Sprawdza czy błąd wskazuje na niedostępny, niewspierany model lub wyczerpanie kwoty."""
        message = str(exc).lower()
        return (
            "not_found" in message
            or "is not found" in message
            or "not supported for generatecontent" in message
            or "unexpected model name format" in message
            or "resource_exhausted" in message
            or "quota exceeded" in message
            or "rate limit" in message
            or "429" in message
        )

    @staticmethod
    def _extract_thought_parts(response) -> list:
        """Wyciąga thought parts z odpowiedzi Gemini (potrzebne dla modeli 3.x thinking).

        Thought signatures muszą być zawarte w kolejnych turach multi-turn konwersacji,
        aby modele Gemini 3.x działały poprawnie.
        """
        thought_parts = []
        try:
            candidates = getattr(response, "candidates", []) or []
            for candidate in candidates:
                content = getattr(candidate, "content", None)
                parts = getattr(content, "parts", []) or []
                for part in parts:
                    if getattr(part, "thought", False):
                        thought_parts.append(part)
        except Exception:
            pass
        return thought_parts

    def _generate_content_with_fallback(
        self,
        *,
        contents: Any,
        config: Optional[genai_types.GenerateContentConfig] = None,
        thought_parts: Optional[list] = None,
    ):
        """Wysyła request do Gemini z automatycznym fallbackiem modelu.

        Kolejność prób:
        1. Jeśli model osiągnął limit RPM — natychmiast skocz do następnego.
        2. Jeśli API zwróciło błąd kwalifikujący się do fallbacku — skocz do następnego.
        3. Gdy wszystkie modele wyczerpane (RPM lub błędy) — rzuć wyjątek.

        Args:
            thought_parts: Opcjonalne thought parts z poprzedniej odpowiedzi
                           (wymagane dla multi-turn z modelami Gemini 3.x thinking).
        """
        # Dołącz thought parts z poprzedniej tury na początku contents (multi-turn thinking)
        if thought_parts:
            if isinstance(contents, list):
                contents = thought_parts + contents
            else:
                contents = thought_parts + [contents]
        candidates: list[str] = [self.model_name]
        for candidate in self._fallback_models():
            if candidate not in candidates:
                candidates.append(candidate)

        last_exc: Optional[Exception] = None
        rpm_skipped: list[str] = []

        for idx, candidate_model in enumerate(candidates):
            # Sprawdź limit RPM — bez blokowania, od razu fallback
            if not self._rate_limiter.try_acquire(candidate_model):
                rpm = self._rate_limiter.get_rpm_limit(candidate_model)
                print(
                    f"⏭️ RPM limit ({rpm}/min) dla {candidate_model} wyczerpany. "
                    f"Przeskakuję na kolejny model."
                )
                rpm_skipped.append(candidate_model)
                continue

            try:
                response = self.client.models.generate_content(
                    model=candidate_model,
                    contents=contents,
                    config=config,
                )

                if candidate_model != self.model_name:
                    print(
                        f"⚠️ Model {self.model_name} niedostępny, przełączam na {candidate_model}."
                    )
                    self.model_name = candidate_model

                return response
            except Exception as exc:
                last_exc = exc
                has_next = idx < len(candidates) - 1
                if not has_next or not self._should_try_fallback(exc):
                    raise

        if rpm_skipped and last_exc is None:
            raise RuntimeError(
                f"Wszystkie modele wyczerpały limit RPM: {rpm_skipped}. Spróbuj ponownie za chwilę."
            )

        if last_exc:
            raise last_exc

        raise RuntimeError("Nie udało się wykonać zapytania Gemini: brak modeli do użycia.")

    @classmethod
    def _normalize_model_name(cls, model_name: str) -> str:
        """Normalizuje nazwę modelu do formatu oczekiwanego przez Gemini API."""
        raw = (model_name or "").strip()
        if not raw:
            return cls._DEFAULT_MODEL

        raw = raw.replace("_", "-")
        if raw.lower().startswith("models/"):
            core = raw.split("/", 1)[1]
        else:
            core = raw

        slug = core.strip().lower().replace(" ", "-")
        return f"models/{slug}"

    def _build_generation_config(
        self,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system_instruction: Optional[str] = None,
        thinking_budget: Optional[int] = None,
    ) -> Optional[genai_types.GenerateContentConfig]:
        """
        Buduje konfigurację generowania dla nowego SDK google-genai.

        Args:
            thinking_budget: Budżet tokenów na myślenie dla modeli thinking (gemini-3.x).
                             0 = wyłącz myślenie, None = domyślne zachowanie modelu.
        """
        cfg: Dict[str, Any] = {
            "temperature": (
                temperature
                if temperature is not None
                else self.generation_params.get("temperature", 0.7)
            )
        }

        tokens = (
            max_tokens
            if max_tokens is not None
            else self.generation_params.get("max_output_tokens")
        )
        if tokens:
            cfg["max_output_tokens"] = tokens

        if system_instruction:
            cfg["system_instruction"] = system_instruction

        # Konfiguracja myślenia dla modeli Gemini 3.x (thinking models)
        resolved_budget = thinking_budget if thinking_budget is not None else self.generation_params.get("thinking_budget")
        if resolved_budget is not None:
            cfg["thinking_config"] = genai_types.ThinkingConfig(thinking_budget=int(resolved_budget))

        return genai_types.GenerateContentConfig(**cfg) if cfg else None

    def generate_text(
        self, 
        prompt: str, 
        temperature: Optional[float] = None, 
        max_tokens: Optional[int] = None,
        system_instruction: Optional[str] = None
    ) -> str:
        """
        Generuje tekst na podstawie promptu.

        Args:
            prompt: Prompt dla modelu.
            temperature: Temperatura generowania (0.0-1.0). Jeśli None, użyje wartości z konfiguracji.
            max_tokens: Maksymalna liczba tokenów (opcjonalne). Jeśli None, użyje wartości z konfiguracji.
            system_instruction: Instrukcja systemowa dla modelu (opcjonalne).

        Returns:
            Wygenerowany tekst.
        """
        model_response = None
        try:
            generation_config = self._build_generation_config(
                temperature=temperature,
                max_tokens=max_tokens,
                system_instruction=system_instruction,
            )

            model_response = self._generate_content_with_fallback(
                contents=prompt,
                config=generation_config,
            )

            if getattr(model_response, "text", None):
                return model_response.text

            raise ValueError("Gemini zwrócił pustą odpowiedź tekstową.")
        except Exception as e:
            print(f"Błąd API Gemini (generate_text): {e}")
            try:
                if model_response is not None:
                    print(f"Prompt feedback: {model_response.prompt_feedback}")
            except Exception:
                pass
            raise Exception(f"Błąd generowania tekstu: {e}")

    def _flatten_with_best_background(self, image: Image.Image) -> Image.Image:
        """Spłaszcza przezroczysty obraz na białe lub czarne tło - wybiera to z wyższym kontrastem."""
        # Upewnij się że mamy kanał alfa
        if image.mode == "LA":
            image = image.convert("RGBA")
        alpha = image.split()[-1]
        rgb = image.convert("RGB")

        white_bg = Image.new("RGB", image.size, (255, 255, 255))
        white_bg.paste(rgb, mask=alpha)

        black_bg = Image.new("RGB", image.size, (0, 0, 0))
        black_bg.paste(rgb, mask=alpha)

        white_std = ImageStat.Stat(white_bg.convert("L")).stddev[0]
        black_std = ImageStat.Stat(black_bg.convert("L")).stddev[0]

        chosen = "black" if black_std > white_std else "white"
        print(f"Przezroczystość → tło {chosen} (kontrast: biały={white_std:.1f}, czarny={black_std:.1f})")
        return black_bg if black_std > white_std else white_bg

    def analyze_image(self, image_url: str, prompt: str, system_instruction: Optional[str] = None) -> Dict[str, Any]:
        """
        Analizuje obraz na podstawie dostarczonego promptu.
        Używa PIL do wstępnego przetworzenia obrazu.

        Args:
            image_url: URL obrazu do analizy.
            prompt: Prompt zawierający instrukcje dla modelu.
            system_instruction: Instrukcja systemowa dla modelu (opcjonalne).

        Returns:
            Słownik z przeanalizowanymi danymi (wynik parsowania JSON).
        """
        model_response = None
        try:
            # Pobierz obraz
            image_response = requests.get(image_url, timeout=10)
            image_response.raise_for_status()  # Sprawdź czy pobieranie się udało

            # Otwórz obraz za pomocą PIL
            image = Image.open(BytesIO(image_response.content))

            # Opcjonalna optymalizacja: zmniejsz rozmiar jeśli obraz jest bardzo duży
            max_size = (2048, 2048)
            if image.width > max_size[0] or image.height > max_size[1]:
                print(f"Zmniejszam obraz z {image.size} do maks. {max_size}")
                image.thumbnail(max_size, Image.Resampling.LANCZOS)

            # Spłaszcz przezroczystość do RGB z optymalnym tłem
            if image.mode == "P":
                image = image.convert("RGBA")

            if image.mode in ("RGBA", "LA"):
                image = self._flatten_with_best_background(image)
            elif image.mode != "RGB":
                image = image.convert("RGB")

            # Zapisz przetworzone zdjęcie do bajtów
            buffer = BytesIO()
            image.save(buffer, format="JPEG", quality=90)
            content_type = "image/jpeg"
            image_bytes = buffer.getvalue()

            print(f"✅ Przetworzono obraz: rozmiar={len(image_bytes)} bajtów, wymiary={image.size}")

            # Przygotuj content dla API
            content = [prompt, genai_types.Part.from_bytes(data=image_bytes, mime_type=content_type)]

            generation_config = self._build_generation_config(system_instruction=system_instruction)

            # Wyślij do Gemini
            model_response = self._generate_content_with_fallback(
                contents=content,
                config=generation_config,
            )

            # Wyczyść i sparsuj odpowiedź JSON
            response_text = (getattr(model_response, "text", "") or "").strip()
            response_text = response_text.replace("```json", "").replace("```", "")

            if not response_text:
                raise ValueError("Gemini zwrócił pustą odpowiedź dla analizy obrazu.")

            try:
                parsed_result = json.loads(response_text)

                # Sprawdź czy Gemini zwrócił informację o braku aktywności
                if not parsed_result.get("typ_aktywnosci") or not parsed_result.get("dystans"):
                    print(
                        f"⚠️ Gemini nie wykrył aktywności: {parsed_result.get('komentarz', 'Brak danych')}"
                    )
                    return parsed_result  # Zwróć wynik z null wartościami

                return parsed_result

            except json.JSONDecodeError as e:
                print(f"❌ Błąd parsowania JSON z odpowiedzi Gemini: {e}")
                print(f"Surowa odpowiedź: {response_text[:500]}")
                # Zwróć strukturę wskazującą na brak danych zamiast rzucania wyjątku
                return {
                    "typ_aktywnosci": None,
                    "dystans": None,
                    "komentarz": "Błąd analizy obrazu - nie udało się przetworzyć odpowiedzi",
                }

        except requests.exceptions.RequestException as e:
            print(f"❌ Błąd pobierania obrazu z URL: {e}")
            return {"typ_aktywnosci": None, "dystans": None, "komentarz": "Błąd pobierania obrazu"}
        except Exception as e:
            print(f"❌ Błąd API Gemini (analyze_image): {e}")
            try:
                if model_response is not None:
                    print(f"Prompt feedback: {model_response.prompt_feedback}")
            except Exception:
                pass
            return {"typ_aktywnosci": None, "dystans": None, "komentarz": "Błąd analizy obrazu"}

    def analyze_image_with_better_model(
        self, 
        image_url: str, 
        prompt: str, 
        system_instruction: Optional[str] = None,
        better_model: str = "models/gemini-2.0-flash"
    ) -> Dict[str, Any]:
        """Analizuje obraz używając lepszego modelu (retry dla problemów z kontrastem)."""
        # Tymczasowo zmień model
        original_model = self.model_name
        self.model_name = self._normalize_model_name(better_model)
        
        try:
            print(f"🔄 Retrying image analysis with better model: {better_model}")
            result = self.analyze_image(image_url, prompt, system_instruction)
            return result
        finally:
            # Przywróć oryginalny model
            self.model_name = original_model

    def get_model_info(self) -> Dict[str, Any]:
        """Zwraca informacje o używanym modelu."""
        return {
            "model_name": self.model_name,
            "credentials_type": "API Key",
            "supports_system_instruction": True,
        }

    def list_available_models(self):
        """Wyświetla dostępne modele Gemini, które wspierają generowanie treści."""
        print("Dostępne modele Gemini (do generowania treści):")
        for m in self.client.models.list():
            supported_actions = getattr(m, "supported_actions", []) or []
            if "generateContent" in supported_actions:
                print(f"- {m.name}")


def main():
    """Funkcja testowa demonstrująca użycie uproszczonego klienta."""
    try:
        print("🔄 Inicjalizacja klienta Gemini...")
        client = GeminiClient()
        print(f"✅ Klient zainicjalizowany. Model: {client.model_name}")

        # Test 1: Listowanie modeli
        print("\n🤖 Test 1: Listowanie dostępnych modeli")
        client.list_available_models()

        # Test 2: Generowanie tekstu
        print("\n📝 Test 2: Generowanie prostego tekstu")
        prompt_text = "Napisz krótki, motywujący cytat o sporcie."
        generated_text = client.generate_text(prompt_text)
        print(f"Prompt: '{prompt_text}'")
        print(f"Odpowiedź: {generated_text}")

        # Test 3: Analiza obrazu (wymaga URL)
        print("\n📸 Test 3: Analiza obrazu (przykładowy prompt)")
        print("⚠️  Wymaga prawdziwego URL do zdjęcia z aktywnością sportową.")
        image_url = "https://i.imgur.com/c4b8jZg.png"  # Przykładowy URL, może nie działać

        analysis_prompt = """Przeanalizuj to zdjęcie aktywności sportowej.
Wyciągnij następujące informacje i zwróć TYLKO obiekt JSON:
{
  "typ_aktywnosci": "jeden z [bieganie_teren, bieganie_bieznia, rower]",
  "dystans": float
}"""
        try:
            analysis_result = client.analyze_image(image_url, analysis_prompt)
            print("Wynik analizy obrazu:")
            print(json.dumps(analysis_result, indent=2))
        except Exception as e:
            print(
                f"Nie udało się przeanalizować obrazu (to normalne, jeśli URL jest nieaktywny): {e}"
            )

        print("\n✅ Testy zakończone!")

    except ValueError as e:
        print(f"❌ Błąd konfiguracji: {e}")
    except Exception as e:
        print(f"❌ Wystąpił nieoczekiwany błąd: {e}")


if __name__ == "__main__":
    main()
