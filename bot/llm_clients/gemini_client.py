"""Szczypior Discord Bot - Klient Gemini AI."""

import json
import os
from io import BytesIO
from typing import Any, Dict, Optional

import google.generativeai as genai
import requests
from dotenv import load_dotenv
from PIL import Image

from .base_client import BaseLLMClient

# Wczytaj zmienne środowiskowe
load_dotenv()


class GeminiClient(BaseLLMClient):
    """Klient do komunikacji z Google Gemini AI."""

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

        genai.configure(api_key=api_key)

        # Ustaw domyślny model jeśli nie podano
        if not self.model_name:
            self.model_name = "gemini-1.5-flash"

        # Zapisz parametry generowania
        self.generation_params = generation_params or {}
        
        # Model będzie tworzony dynamicznie z system_instruction w metodach

    def _create_model(self, system_instruction: Optional[str] = None) -> genai.GenerativeModel:
        """
        Tworzy instancję modelu z opcjonalną instrukcją systemową.
        
        Args:
            system_instruction: Instrukcja systemowa dla modelu
            
        Returns:
            Instancja GenerativeModel
        """
        if system_instruction:
            return genai.GenerativeModel(
                self.model_name,
                system_instruction=system_instruction
            )
        return genai.GenerativeModel(self.model_name)

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
        try:
            # Utwórz model z system_instruction jeśli podano
            model = self._create_model(system_instruction)
            
            # Użyj wartości z argumentów lub z konfiguracji
            generation_config = {
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
                generation_config["max_output_tokens"] = tokens

            response = model.generate_content(prompt, generation_config=generation_config)
            return response.text
        except Exception as e:
            print(f"Błąd API Gemini (generate_text): {e}")
            try:
                print(f"Prompt feedback: {response.prompt_feedback}")
            except:
                pass
            raise Exception(f"Błąd generowania tekstu: {e}")

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
        try:
            # Utwórz model vision z system_instruction jeśli podano
            vision_model = self._create_model(system_instruction)
            
            # Pobierz obraz
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()  # Sprawdź czy pobieranie się udało

            # Otwórz obraz za pomocą PIL
            image = Image.open(BytesIO(response.content))

            # Opcjonalna optymalizacja: zmniejsz rozmiar jeśli obraz jest bardzo duży
            max_size = (2048, 2048)
            if image.width > max_size[0] or image.height > max_size[1]:
                print(f"Zmniejszam obraz z {image.size} do maks. {max_size}")
                image.thumbnail(max_size, Image.Resampling.LANCZOS)

            # Konwertuj do RGB jeśli potrzeba (usuwa kanał alpha)
            if image.mode in ("RGBA", "LA", "P"):
                print(f"Konwertuję obraz z {image.mode} do RGB")
                background = Image.new("RGB", image.size, (255, 255, 255))
                if image.mode == "P":
                    image = image.convert("RGBA")
                background.paste(
                    image, mask=image.split()[-1] if image.mode in ("RGBA", "LA") else None
                )
                image = background

            # Zapisz przetworzone zdjęcie do bajtów
            buffer = BytesIO()
            image.save(buffer, format="JPEG", quality=85)
            image_bytes = buffer.getvalue()
            content_type = "image/jpeg"

            print(f"✅ Przetworzono obraz: rozmiar={len(image_bytes)} bajtów, wymiary={image.size}")

            # Przygotuj content dla API
            content = [prompt, {"mime_type": content_type, "data": image_bytes}]

            # Wyślij do Gemini
            response = vision_model.generate_content(content)

            # Wyczyść i sparsuj odpowiedź JSON
            response_text = response.text.strip().replace("```json", "").replace("```", "")

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
                print(f"Prompt feedback: {response.prompt_feedback}")
            except:
                pass
            return {"typ_aktywnosci": None, "dystans": None, "komentarz": "Błąd analizy obrazu"}

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
        for m in genai.list_models():
            if "generateContent" in m.supported_generation_methods:
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
