"""Moduł pomocniczy zawierający wspólne funkcje wykorzystywane w całym projekcie."""

from functools import wraps
from typing import Any, Dict, List, Optional, Union

import discord


def get_display_name(user: Union[discord.User, discord.Member]) -> str:
    """
    Pobiera wyświetlaną nazwę użytkownika (display_name uwzględnia nick/alias na serwerze).

    Args:
        user: Obiekt użytkownika Discord (User lub Member)

    Returns:
        Wyświetlana nazwa użytkownika (nick jeśli ustawiony, inaczej global_name lub username)
    """
    # Member ma display_name który uwzględnia nick (alias) na serwerze
    if hasattr(user, "display_name"):
        return user.display_name
    # Fallback dla User (bez kontekstu serwera)
    return user.global_name if user.global_name else str(user)


def format_distance(distance: Union[float, str], decimal_places: int = 1) -> str:
    """
    Formatuje dystans do polskiego formatu (z przecinkiem).

    Args:
        distance: Dystans jako float lub string
        decimal_places: Liczba miejsc po przecinku

    Returns:
        Sformatowany string dystansu
    """
    try:
        if isinstance(distance, str):
            distance = float(distance.replace(",", "."))
        return f"{distance:.{decimal_places}f}".replace(".", ",")
    except (ValueError, AttributeError):
        return "0,0"


def parse_distance(distance: Union[float, str, int]) -> float:
    """
    Konwertuje dystans ze stringa lub inta na float.
    Obsługuje polski format (przecinek) i międzynarodowy (kropka).

    Args:
        distance: Dystans jako string, float lub int

    Returns:
        Dystans jako float
    """
    try:
        if isinstance(distance, str):
            return float(distance.replace(",", "."))
        return float(distance)
    except (ValueError, AttributeError, TypeError):
        return 0.0


def safe_int(value: Any, default: int = 0) -> int:
    """
    Bezpiecznie konwertuje wartość na int.

    Args:
        value: Wartość do konwersji
        default: Wartość domyślna jeśli konwersja się nie powiedzie

    Returns:
        Skonwertowana wartość lub default
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def create_embed(
    title: str,
    description: Optional[str] = None,
    color: Optional[discord.Color] = None,
    fields: Optional[List[Dict[str, Any]]] = None,
    footer: Optional[str] = None,
) -> discord.Embed:
    """
    Tworzy embed Discord z podanymi parametrami.

    Args:
        title: Tytuł embedu
        description: Opis embedu
        color: Kolor embedu (domyślnie zielony)
        fields: Lista słowników z polami {name, value, inline}
        footer: Tekst stopki

    Returns:
        Obiekt discord.Embed
    """
    if color is None:
        color = discord.Color.green()

    embed = discord.Embed(title=title, description=description, color=color)

    if fields:
        for field in fields:
            embed.add_field(
                name=field.get("name", "Pole"),
                value=field.get("value", "-"),
                inline=field.get("inline", True),
            )

    if footer:
        embed.set_footer(text=footer)

    return embed


def create_activity_embed(
    activity_info: Dict[str, Any],
    username: str,
    distance: float,
    points: int,
    additional_fields: Optional[List[Dict[str, Any]]] = None,
    saved: bool = True,
) -> discord.Embed:
    """
    Tworzy standardowy embed dla aktywności.

    Args:
        activity_info: Słownik z informacjami o typie aktywności (z ACTIVITY_TYPES)
        username: Nazwa użytkownika (mention lub string)
        distance: Dystans aktywności
        points: Punkty za aktywność
        additional_fields: Dodatkowe pola do embedu
        saved: Czy aktywność została zapisana do arkusza

    Returns:
        Obiekt discord.Embed
    """
    embed = discord.Embed(
        title=f"{activity_info['emoji']} Aktywność dodana!",
        color=discord.Color.green() if saved else discord.Color.orange(),
    )

    # Podstawowe pola
    embed.add_field(name="Użytkownik", value=username, inline=True)
    embed.add_field(name="Typ", value=activity_info["display_name"], inline=True)
    embed.add_field(name=f"Dystans ({activity_info['unit']})", value=f"{distance}", inline=True)

    # Dodatkowe pola
    if additional_fields:
        for field in additional_fields:
            embed.add_field(
                name=field.get("name", "Pole"),
                value=field.get("value", "-"),
                inline=field.get("inline", True),
            )

    # Punkty
    embed.add_field(name="Punkty", value=f"🏆 **{points}**", inline=False)

    # Stopka jeśli nie zapisano
    if not saved:
        embed.set_footer(text="⚠️ Dane nie zostały zapisane do Google Sheets")

    return embed


def handle_sheets_error(func):
    """
    Dekorator do obsługi błędów związanych z Google Sheets.

    Args:
        func: Funkcja do ozdobienia

    Returns:
        Ozdobiona funkcja z obsługą błędów
    """

    @wraps(func)
    async def wrapper(ctx, *args, **kwargs):
        try:
            # Sprawdź czy sheets_manager istnieje w kontekście
            bot = ctx.bot
            if not hasattr(bot, "sheets_manager") or bot.sheets_manager is None:
                await ctx.send("❌ Google Sheets nie jest skonfigurowany.")
                return None
            return await func(ctx, *args, **kwargs)
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Error in {func.__name__}", exc_info=True)
            await ctx.send(f"❌ Wystąpił błąd podczas wykonywania komendy: {e}")
            return None

    return wrapper


def format_activity_summary(record: Dict[str, Any]) -> str:
    """
    Formatuje pojedynczą aktywność do krótkiego podsumowania.

    Args:
        record: Słownik z danymi aktywności

    Returns:
        Sformatowany string z podsumowaniem
    """
    activity = record.get("Aktywność", record.get("Rodzaj Aktywności", "N/A"))
    distance = parse_distance(record.get("Dystans (km)", 0))
    points = safe_int(record.get("Punkty", record.get("PUNKTY", 0)))
    date = record.get("Data", "N/A")

    return f"{date}: {activity} {format_distance(distance)}km, {points} pkt"


def aggregate_by_field(
    records: List[Dict[str, Any]], group_field: str, sum_fields: Optional[List[str]] = None
) -> Dict[str, Dict[str, Any]]:
    """
    Agreguje rekordy według pola grupującego i sumuje wybrane pola.

    Args:
        records: Lista słowników z danymi
        group_field: Nazwa pola do grupowania
        sum_fields: Lista nazw pól do sumowania

    Returns:
        Słownik z zagregowanymi danymi {group_value: {field: sum, ...}}
    """
    if sum_fields is None:
        sum_fields = ["Dystans (km)", "Punkty", "PUNKTY"]

    aggregated = {}

    for record in records:
        group_value = record.get(group_field, "Unknown")
        if not group_value:
            continue

        if group_value not in aggregated:
            aggregated[group_value] = {"count": 0, "total_distance": 0, "total_points": 0}

        aggregated[group_value]["count"] += 1

        # Sumuj dystans
        distance = parse_distance(record.get("Dystans (km)", 0))
        aggregated[group_value]["total_distance"] += distance

        # Sumuj punkty (obsługuj różne nazwy kolumn)
        points = safe_int(record.get("Punkty", record.get("PUNKTY", 0)))
        aggregated[group_value]["total_points"] += points

    return aggregated


def calculate_user_totals(records: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Oblicza totalne statystyki dla każdego użytkownika.

    Args:
        records: Lista wszystkich rekordów

    Returns:
        Słownik {username: {total_points, total_distance, count}}
    """
    return aggregate_by_field(records, "Nick")
