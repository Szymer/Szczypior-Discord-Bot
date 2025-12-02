"""Szczypior Discord Bot - Klient Gemini AI."""

import os
from typing import Optional, List, Dict, Any
import google.generativeai as genai
from dotenv import load_dotenv

# Wczytaj zmienne środowiskowe
load_dotenv()


class GeminiClient:
    """Klient do komunikacji z Google Gemini AI."""
    
    def __init__(self, model_name: str = "gemini-2.5-flash", 
                 system_instruction: Optional[str] = None):
        """
        Inicjalizuje klienta Gemini.
        
        Args:
            model_name: Nazwa modelu Gemini do użycia
            system_instruction: System prompt/instrukcja dla modelu
        """
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("Nie znaleziono klucza GEMINI_API_KEY w zmiennych środowiskowych.")
            
        # Konfiguracja Gemini
        genai.configure(api_key=api_key)
        
        # Domyślna instrukcja systemowa dla analizy aktywności sportowych
        if system_instruction is None:
            system_instruction = """Jesteś asystentem AI specjalizującym się w analizie aktywności sportowych.
Twoim zadaniem jest dokładne wyciąganie informacji z opisów treningów i aktywności fizycznych.

WAŻNE ZASADY:
1. Zawsze zwracaj dane w formacie JSON
2. Typ aktywności musi być jednym z: bieganie_teren, bieganie_bieznia, plywanie, rower, spacer, cardio
3. Dystans zawsze w kilometrach (km)
4. Obciążenie w kilogramach (kg)
5. Przewyższenie w metrach (m)
6. Jeśli brak informacji, zwróć null
7. Bądź konserwatywny - lepiej zwrócić null niż zgadywać
8. Dla zdjęć bez tekstu, analizuj widoczne dane z aplikacji sportowych"""
        
        # Inicjalizacja modelu
        self.model_name = model_name
        self.system_instruction = system_instruction
        self.model = genai.GenerativeModel(model_name)
        
        # Historia konwersacji (opcjonalne)
        self.chat_history: List[Dict[str, str]] = []


    
    def generate_text(self, prompt: str, temperature: float = 0.7, 
                     max_tokens: Optional[int] = None) -> str:
        """
        Generuje tekst na podstawie promptu.
        
        Args:
            prompt: Prompt dla modelu
            temperature: Temperatura generowania (0.0-1.0)
            max_tokens: Maksymalna liczba tokenów (opcjonalne)
            
        Returns:
            Wygenerowany tekst
        """
        try:
            generation_config = {
                "temperature": temperature,
            }
            if max_tokens:
                generation_config["max_output_tokens"] = max_tokens
            
            response = self.model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            return response.text
        except Exception as e:
            raise Exception(f"Błąd generowania tekstu: {e}")
    
    def chat(self, message: str, use_history: bool = True) -> str:
        """
        Prowadzi konwersację z modelem z zachowaniem historii.
        
        Args:
            message: Wiadomość użytkownika
            use_history: Czy używać historii konwersacji
            
        Returns:
            Odpowiedź modelu
        """
        try:
            if use_history and self.chat_history:
                # Użyj chat session z historią
                chat = self.model.start_chat(history=self._format_history())
                response = chat.send_message(message)
            else:
                # Pojedyncze zapytanie bez historii
                response = self.model.generate_content(message)
            
            # Dodaj do historii
            if use_history:
                self.chat_history.append({"role": "user", "content": message})
                self.chat_history.append({"role": "assistant", "content": response.text})
            
            return response.text
        except Exception as e:
            raise Exception(f"Błąd czatu: {e}")
    
    def _format_history(self) -> List[Dict[str, str]]:
        """
        Formatuje historię konwersacji dla Gemini API.
        
        Returns:
            Lista z historią w formacie Gemini
        """
        formatted = []
        for entry in self.chat_history:
            formatted.append({
                "role": "user" if entry["role"] == "user" else "model",
                "parts": [entry["content"]]
            })
        return formatted
    
    def clear_history(self):
        """Czyści historię konwersacji."""
        self.chat_history = []
    
    def analyze_activity_from_image(self, image_url: str, text_context: Optional[str] = None) -> Dict[str, Any]:
        """
        Analizuje obraz aktywności sportowej (screenshot z aplikacji, zdjęcie).
        
        Args:
            image_url: URL obrazu do analizy
            text_context: Opcjonalny tekst towarzyszący obrazowi
            
        Returns:
            Słownik z informacjami o aktywności
        """
        try:
            import requests
            from PIL import Image
            from io import BytesIO
            
            # Pobierz obraz
            response = requests.get(image_url)
            image_bytes = response.content
            
            # Określ typ MIME na podstawie Content-Type
            content_type = response.headers.get('content-type', 'image/jpeg')
            
            # Przygotuj prompt
            if text_context:
                prompt_text = f"""Przeanalizuj to zdjęcie aktywności sportowej wraz z kontekstem tekstowym.

Tekst użytkownika: "{text_context}"

Wyciągnij następujące informacje i zwróć TYLKO obiekt JSON (bez markdown):
{{
  "typ_aktywnosci": "jeden z [bieganie_teren, bieganie_bieznia, plywanie, rower, spacer, cardio]",
  "dystans": float,
  "czas": "string lub null",
  "tempo": "string lub null",
  "obciazenie": float lub null,
  "przewyzszenie": float lub null,
  "kalorie": int lub null,
  "puls_sredni": int lub null,
  "komentarz": "string"
}}

WAŻNE:
- Przeanalizuj dokładnie dane widoczne na zdjęciu (aplikacja Garmin, Strava, itp.)
- Jeśli dane nie są widoczne, zwróć null
- Dystans ZAWSZE w kilometrach
- Bądź precyzyjny - przepisuj dokładne wartości ze zdjęcia
- Zwróć TYLKO JSON, bez ```json ani innych formatowań"""
            else:
                prompt_text = """Przeanalizuj to zdjęcie aktywności sportowej.

Wyciągnij następujące informacje i zwróć TYLKO obiekt JSON (bez markdown):
{
  "typ_aktywnosci": "jeden z [bieganie_teren, bieganie_bieznia, plywanie, rower, spacer, cardio]",
  "dystans": float,
  "czas": "string lub null",
  "tempo": "string lub null",
  "obciazenie": float lub null,
  "przewyzszenie": float lub null,
  "kalorie": int lub null,
  "puls_sredni": int lub null,
  "komentarz": "string"
}

WAŻNE:
- Przeanalizuj dokładnie dane widoczne na zdjęciu (aplikacja Garmin, Strava, itp.)
- Jeśli dane nie są widoczne, zwróć null
- Dystans ZAWSZE w kilometrach
- Bądź precyzyjny - przepisuj dokładne wartości ze zdjęcia
- Zwróć TYLKO JSON, bez ```json ani innych formatowań"""
            
            # Użyj generative model dla vision
            vision_model = genai.GenerativeModel("models/gemini-2.5-flash-image-preview")
            
            # Przygotuj content w poprawnej strukturze
            content = [
                {
                    "role": "user",
                    "parts": [
                        {"text": prompt_text},
                        {"mime_type": content_type, "data": image_bytes}
                    ]
                }
            ]
            
            # Wyślij do Gemini z obrazem
            response = vision_model.generate_content(
                content,
                # generation_config={"temperature": 0.1}
            )
            
            # Parsuj JSON
            import json
            response_clean = response.text.strip()
            if response_clean.startswith("```json"):
                response_clean = response_clean[7:]
            if response_clean.startswith("```"):
                response_clean = response_clean[3:]
            if response_clean.endswith("```"):
                response_clean = response_clean[:-3]
            
            return json.loads(response_clean.strip())
        except Exception as e:
            raise Exception(f"Błąd analizy obrazu: {e}")
    
    def generate_motivational_comment(self, current_activity: Dict[str, Any], 
                                     previous_activities: List[Dict[str, Any]]) -> str:
        """
        Generuje spersonalizowany komentarz motywacyjny na podstawie historii.
        
        Args:
            current_activity: Aktualna aktywność (dict z danymi)
            previous_activities: Lista poprzednich aktywności użytkownika
            
        Returns:
            Motywująca wiadomość uwzględniająca kontekst
        """
        # Przygotuj kontekst z historii
        if previous_activities:
            # Weź ostatnie 5 aktywności
            recent = previous_activities[-5:] if len(previous_activities) > 5 else previous_activities
            history_summary = []
            
            for act in recent:
                history_summary.append(
                    f"- {act.get('Aktywność', 'N/A')}: {act.get('Dystans (km)', 0)} km, "
                    f"{act.get('Punkty', 0)} pkt (Data: {act.get('Data', 'N/A')})"
                )
            
            history_text = "\n".join(history_summary)
            total_distance = sum(float(act.get('Dystans (km)', 0)) for act in previous_activities)
            total_points = sum(int(act.get('Punkty', 0)) for act in previous_activities)
            activity_count = len(previous_activities)
        else:
            history_text = "To pierwsza zarejestrowana aktywność!"
            total_distance = 0
            total_points = 0
            activity_count = 0
        
        prompt = f"""Napisz krótki (2-4 zdania), motywujący komentarz dla użytkownika.

AKTUALNA AKTYWNOŚĆ:
- Typ: {current_activity.get('typ_aktywnosci', 'nieznany')}
- Dystans: {current_activity.get('dystans', 0)} km
- Punkty: {current_activity.get('punkty', 0)}

HISTORIA UŻYTKOWNIKA:
- Łącznie aktywności: {activity_count}
- Łączny dystans: {total_distance:.1f} km
- Łączne punkty: {total_points}

Ostatnie aktywności:
{history_text}

WYTYCZNE:
- Bądź entuzjastyczny i wspierający
- Odnieś się do postępów (jeśli widoczne)
- Zachęć do kontynuacji
- Użyj naturalnego, przyjacielskiego języka
- Jeśli to pierwsza aktywność, powitaj i zmotywuj
- Jeśli użytkownik poprawia wyniki, to podkreśl
- Dodaj emoji dla lepszego efektu (max 2-3)"""
        
        return self.generate_text(prompt, temperature=0.8, max_tokens=200)
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Zwraca informacje o używanym modelu.
        
        Returns:
            Słownik z informacjami o modelu
        """
        return {
            "model_name": self.model_name,
            "credentials_type": "API Key",
            "chat_history_length": len(self.chat_history)
        }

    def list_available_models(self):
        """Wyświetla dostępne modele Gemini."""
        print("Dostępne modele Gemini:")
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"- {m.name}")


def main():
    """Funkcja testowa demonstrująca użycie klienta."""
    try:
        # Inicjalizacja klienta
        print("🔄 Inicjalizacja klienta Gemini...")
        client = GeminiClient()
        print(f"✅ Klient zainicjalizowany: {client.model_name}")

        # Test 0: Listowanie modeli
        print("\n🤖 Test 0: Listowanie dostępnych modeli")
        client.list_available_models()
        
        # Test 1: Analiza obrazu (przykładowy URL)
        print("\n📸 Test 1: Analiza obrazu aktywności")
        print("⚠️  Wymaga prawdziwego URL do zdjęcia z aktywności")
        
        # Test 2: Generowanie komentarza z kontekstem
        print("\n💬 Test 2: Komentarz motywacyjny z historią")
        current = {
            "typ_aktywnosci": "bieganie_teren",
            "dystans": 10.5,
            "punkty": 10500
        }
        history = [
            {"Aktywność": "bieganie_teren", "Dystans (km)": 8.0, "Punkty": 8000, "Data": "2025-11-28"},
            {"Aktywność": "bieganie_teren", "Dystans (km)": 9.2, "Punkty": 9200, "Data": "2025-11-30"},
        ]
        comment = client.generate_motivational_comment(current, history)
        print(f"Komentarz: {comment}")
        
        # Informacje o modelu
        print("\n📋 Informacje o modelu:")
        info = client.get_model_info()
        for key, value in info.items():
            print(f"  {key}: {value}")
        
        print("\n✅ Testy zakończone!")
        
    except ValueError as e:
        print(f"❌ Błąd konfiguracji: {e}")
        print("\nAby użyć klienta Gemini:")
        print("1. Uzyskaj klucz API z: https://aistudio.google.com/app/apikey")
        print("2. Dodaj do pliku .env: GEMINI_API_KEY=twój_klucz")
    except Exception as e:
        print(f"❌ Błąd: {e}")


if __name__ == "__main__":
    main()
