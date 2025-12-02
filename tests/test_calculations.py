"""Testy dla systemu kalkulacji punktów."""

import sys
import os

# Dodaj katalog główny do ścieżki
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bot.main import calculate_points, ACTIVITY_TYPES


def test_bieganie_teren_basic():
    """Test podstawowej kalkulacji dla biegania w terenie."""
    points, error = calculate_points("bieganie_teren", 10)
    assert error == "", f"Nie powinno być błędu: {error}"
    assert points == 10000, f"Oczekiwano 10000 (10km * 1000), otrzymano {points}"


def test_bieganie_bieznia_basic():
    """Test podstawowej kalkulacji dla biegania na bieżni."""
    points, error = calculate_points("bieganie_bieznia", 10)
    assert error == "", f"Nie powinno być błędu: {error}"
    assert points == 8000, f"Oczekiwano 8000 (10km * 800), otrzymano {points}"


def test_plywanie_basic():
    """Test dla pływania."""
    points, error = calculate_points("plywanie", 2)
    assert error == "", f"Nie powinno być błędu: {error}"
    assert points == 8000, f"Oczekiwano 8000 (2km * 4000), otrzymano {points}"


def test_rower_min_distance():
    """Test minimalnego dystansu dla roweru."""
    points, error = calculate_points("rower", 5)
    assert "Minimalny dystans" in error, f"Powinien być błąd minimalnego dystansu, otrzymano: {error}"
    assert points == 0, f"Punkty powinny być 0 dla dystansu poniżej minimum"


def test_rower_valid_distance():
    """Test poprawnego dystansu dla roweru."""
    points, error = calculate_points("rower", 20)
    assert error == "", f"Nie powinno być błędu: {error}"
    assert points == 6000, f"Oczekiwano 6000 (20km * 300), otrzymano {points}"


def test_spacer_min_distance():
    """Test minimalnego dystansu dla spaceru."""
    points, error = calculate_points("spacer", 2)
    assert "Minimalny dystans" in error, f"Powinien być błąd minimalnego dystansu"
    assert points == 0, f"Punkty powinny być 0 dla dystansu poniżej minimum"


def test_spacer_valid_distance():
    """Test poprawnego dystansu dla spaceru."""
    points, error = calculate_points("spacer", 5)
    assert error == "", f"Nie powinno być błędu: {error}"
    assert points == 1000, f"Oczekiwano 1000 (5km * 200), otrzymano {points}"


def test_bieganie_with_weight():
    """Test biegania z obciążeniem."""
    points, error = calculate_points("bieganie_teren", 10, weight=10)
    assert error == "", f"Nie powinno być błędu: {error}"
    # 10km * 1000 = 10000, bonus: (10kg/5) * (10*1000*0.1) = 2 * 1000 = 2000
    # Total: 12000
    assert points == 12000, f"Oczekiwano 12000, otrzymano {points}"


def test_bieganie_with_elevation():
    """Test biegania z przewyższeniem."""
    points, error = calculate_points("bieganie_teren", 10, elevation=200)
    assert error == "", f"Nie powinno być błędu: {error}"
    # 10km * 1000 = 10000, bonus: (200m/100) * (10*1000*0.05) = 2 * 500 = 1000
    # Total: 11000
    assert points == 11000, f"Oczekiwano 11000, otrzymano {points}"


def test_plywanie_no_bonuses():
    """Test - pływanie nie powinno mieć bonusów."""
    points, error = calculate_points("plywanie", 2, weight=5, elevation=100)
    # Powinien być błąd bo pływanie nie wspiera bonusów
    assert error != "", f"Powinien być błąd dla niewspieranych bonusów"


def test_invalid_activity():
    """Test dla nieznanego typu aktywności."""
    points, error = calculate_points("nieznana_aktywnosc", 10)
    assert points == 0, f"Dla nieznanej aktywności oczekiwano 0, otrzymano {points}"
    assert "Nieznany typ" in error, f"Powinien być błąd o nieznanym typie"


def test_cardio_basic():
    """Test dla cardio."""
    points, error = calculate_points("cardio", 5)
    assert error == "", f"Nie powinno być błędu: {error}"
    assert points == 4000, f"Oczekiwano 4000 (5km * 800), otrzymano {points}"


def test_all_activities_structure():
    """Test czy wszystkie typy aktywności mają wymagane pola."""
    required_fields = ['emoji', 'base_points', 'unit', 'min_distance', 'bonuses', 'display_name']
    
    for activity, info in ACTIVITY_TYPES.items():
        for field in required_fields:
            assert field in info, f"Aktywność {activity} nie ma pola {field}"
        assert isinstance(info['base_points'], int), f"base_points dla {activity} musi być int"
        assert info['base_points'] > 0, f"base_points dla {activity} musi być > 0"
        assert isinstance(info['bonuses'], list), f"bonuses dla {activity} musi być listą"


if __name__ == "__main__":
    # Uruchom wszystkie testy
    test_functions = [
        test_bieganie_teren_basic,
        test_bieganie_bieznia_basic,
        test_plywanie_basic,
        test_rower_min_distance,
        test_rower_valid_distance,
        test_spacer_min_distance,
        test_spacer_valid_distance,
        test_bieganie_with_weight,
        test_bieganie_with_elevation,
        test_plywanie_no_bonuses,
        test_invalid_activity,
        test_cardio_basic,
        test_all_activities_structure,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in test_functions:
        try:
            test_func()
            print(f"✅ {test_func.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"❌ {test_func.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ {test_func.__name__}: Błąd: {e}")
            failed += 1
    
    print(f"\n{'='*50}")
    print(f"Wyniki testów: {passed} ✅ | {failed} ❌")
    print(f"{'='*50}")
    
    if failed > 0:
        sys.exit(1)
