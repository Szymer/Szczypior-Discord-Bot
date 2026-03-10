"""Shared constants copied from discord-bot domain model."""

ACTIVITY_TYPES = {
    "bieganie_teren": {
        "emoji": "🏃",
        "base_points": 1000,
        "unit": "km",
        "min_distance": 0,
        "bonuses": ["obciążenie", "przewyższenie"],
        "display_name": "Bieganie (Teren)",
    },
    "bieganie_bieznia": {
        "emoji": "🏃‍♂️",
        "base_points": 800,
        "unit": "km",
        "min_distance": 0,
        "bonuses": ["obciążenie"],
        "display_name": "Bieganie (Bieżnia)",
    },
    "plywanie": {
        "emoji": "🏊",
        "base_points": 4000,
        "unit": "km",
        "min_distance": 0,
        "bonuses": [],
        "display_name": "Pływanie",
    },
    "rower": {
        "emoji": "🚴",
        "base_points": 300,
        "unit": "km",
        "min_distance": 6,
        "bonuses": ["przewyższenie"],
        "display_name": "Rower/Rolki",
    },
    "spacer": {
        "emoji": "🚶",
        "base_points": 200,
        "unit": "km",
        "min_distance": 3,
        "bonuses": ["obciążenie", "przewyższenie"],
        "display_name": "Spacer/Trekking",
    },
    "cardio": {
        "emoji": "🔫",
        "base_points": 800,
        "unit": "km",
        "min_distance": 0,
        "bonuses": ["obciążenie", "przewyższenie"],
        "display_name": "Inne Cardio (wioślarz, orbitrek, ASG)",
    },
}
