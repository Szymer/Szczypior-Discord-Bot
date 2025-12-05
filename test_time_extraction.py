"""Test ekstrakcji czasu z komentarzy Gemini."""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bot.orchestrator import BotOrchestrator

# Utwórz mock orchestratora tylko do testowania funkcji
class MockBot:
    pass

class MockGemini:
    pass

class MockSheets:
    pass

orchestrator = BotOrchestrator(MockBot(), MockGemini(), MockSheets())

# Testowe przypadki
test_cases = [
    ("Na zdjęciu widoczne są statystyki aktywności 'Soccer/Football'. Całkowity czas aktywności wynosi 1 godzinę, 12 minut i 56 sekund.", 72.9),
    ("Czas trwania: 1:12:56", 72.9),
    ("Activity time: 1h 12m", 72.0),
    ("Duration: 45:30 (45 minut 30 sekund)", 45.5),
    ("Trening trwał 90 minut", None),  # Ten nie zadziała, bo nie ma specyficznego formatu
    ("Total time: 2 godziny, 30 minut", 150.0),
]

print("🧪 Test ekstrakcji czasu z komentarzy:\n")
for comment, expected in test_cases:
    result = orchestrator._extract_time_from_comment(comment)
    status = "✅" if result == expected or (result and expected and abs(result - expected) < 1) else "❌"
    print(f"{status} '{comment[:60]}...'")
    print(f"   Oczekiwano: {expected} min, Otrzymano: {result} min\n")
