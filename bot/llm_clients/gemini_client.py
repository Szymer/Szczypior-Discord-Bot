"""Szczypior Discord Bot - Klient Gemini AI."""

import os
from typing import Optional, Dict, Any
import google.generativeai as genai
from dotenv import load_dotenv
import requests
import json
from .base_client import BaseLLMClient

# Wczytaj zmienne środowiskowe
load_dotenv()


class GeminiClient(BaseLLMClient):
    """Klient do komunikacji z Google Gemini AI."""
    
    def __init__(self, model_name: Optional[str] = None, generation_params: Optional[Dict[str, Any]] = None, **kwargs):
        """
        Inicjalizuje klienta Gemini.
        
        Args:
            model_name: Nazwa modelu Gemini do użycia.
            generation_params: Parametry generowania (temperature, max_tokens, itp.).
            **kwargs: Dodatkowe argumenty.
        """
        super().__init__(model_name, **kwargs)
        
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("Nie znaleziono klucza GEMINI_API_KEY w zmiennych środowiskowych.")
            
        genai.configure(api_key=api_key)
        
        # Ustaw domyślny model jeśli nie podano
        if not self.model_name:
            self.model_name = "gemini-1.5-flash"
        
        self.model = genai.GenerativeModel(self.model_name)
        self.vision_model = genai.GenerativeModel(self.model_name)
        
        # Zapisz parametry generowania
        self.generation_params = generation_params or {}

    def generate_text(self, prompt: str, temperature: Optional[float] = None, 
                     max_tokens: Optional[int] = None) -> str:
        """
        Generuje tekst na podstawie promptu.
        
        Args:
            prompt: Prompt dla modelu.
            temperature: Temperatura generowania (0.0-1.0). Jeśli None, użyje wartości z konfiguracji.
            max_tokens: Maksymalna liczba tokenów (opcjonalne). Jeśli None, użyje wartości z konfiguracji.
            
        Returns:
            Wygenerowany tekst.
        """
        try:
            # Użyj wartości z argumentów lub z konfiguracji
            generation_config = {
                "temperature": temperature if temperature is not None else self.generation_params.get("temperature", 0.7)
            }
            
            tokens = max_tokens if max_tokens is not None else self.generation_params.get("max_output_tokens")
            if tokens:
                generation_config["max_output_tokens"] = tokens
            
            response = self.model.generate_content(prompt, generation_config=generation_config)
            return response.text
        except Exception as e:
            print(f"Błąd API Gemini (generate_text): {e}")
            try:
                print(f"Prompt feedback: {response.prompt_feedback}")
            except:
                pass
            raise Exception(f"Błąd generowania tekstu: {e}")

    def analyze_image(self, image_url: str, prompt: str) -> Dict[str, Any]:
        """
        Analizuje obraz na podstawie dostarczonego promptu.
        
        Args:
            image_url: URL obrazu do analizy.
            prompt: Prompt zawierający instrukcje dla modelu.
            
        Returns:
            Słownik z przeanalizowanymi danymi (wynik parsowania JSON).
        """
        try:
            # Pobierz obraz
            response = requests.get(image_url)
            response.raise_for_status()  # Sprawdź czy pobieranie się udało
            image_bytes = response.content
            content_type = response.headers.get('content-type', 'image/jpeg')
            
            # Przygotuj content dla API
            content = [
                prompt,
                {"mime_type": content_type, "data": image_bytes}
            ]
            
            # Wyślij do Gemini
            response = self.vision_model.generate_content(content)
            
            # Wyczyść i sparsuj odpowiedź JSON
            response_text = response.text.strip().replace("```json", "").replace("```", "")
            return json.loads(response_text)
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Błąd pobierania obrazu z URL: {e}")
        except json.JSONDecodeError as e:
            raise Exception(f"Błąd parsowania JSON z odpowiedzi Gemini: {e}\nOdpowiedź: {response.text}")
        except Exception as e:
            print(f"Błąd API Gemini (analyze_image): {e}")
            try:
                print(f"Prompt feedback: {response.prompt_feedback}")
            except:
                pass
            raise Exception(f"Błąd analizy obrazu: {e}")

    def get_model_info(self) -> Dict[str, Any]:
        """Zwraca informacje o używanym modelu."""
        return {
            "model_name": self.model_name,
            "vision_model_name": self.vision_model.model_name,
            "credentials_type": "API Key",
        }

    def list_available_models(self):
        """Wyświetla dostępne modele Gemini, które wspierają generowanie treści."""
        print("Dostępne modele Gemini (do generowania treści):")
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
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
        image_url = "https://i.imgur.com/c4b8jZg.png" # Przykładowy URL, może nie działać
        
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
            print(f"Nie udało się przeanalizować obrazu (to normalne, jeśli URL jest nieaktywny): {e}")

        print("\n✅ Testy zakończone!")
        
    except ValueError as e:
        print(f"❌ Błąd konfiguracji: {e}")
    except Exception as e:
        print(f"❌ Wystąpił nieoczekiwany błąd: {e}")


if __name__ == "__main__":
    main()
