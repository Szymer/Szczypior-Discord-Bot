"""Szczypior Discord Bot - Główny plik uruchomieniowy."""

import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from typing import Optional
from .sheets_manager import SheetsManager
from .llm_clients import get_llm_client
from .orchestrator import BotOrchestrator
from .constants import ACTIVITY_TYPES
from .utils import (
    get_display_name, 
    create_embed, 
    create_activity_embed,
    parse_distance,
    safe_int,
    aggregate_by_field,
    calculate_user_totals
)

# Wczytaj zmienne środowiskowe
load_dotenv()

# Konfiguracja bota
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Menedżer Google Sheets
sheets_manager = None

# Klient LLM
llm_client = None

# Orkiestrator
orchestrator = None


@bot.event
async def on_ready():
    """Wywoływane gdy bot jest gotowy."""
    global sheets_manager, llm_client, orchestrator
    print(f"{bot.user} jest online!")
    print(f"ID bota: {bot.user.id}")
    
    # Inicjalizacja Google Sheets (opcjonalne - tylko jeśli skonfigurowane)
    try:
        sheets_manager = SheetsManager()
        sheets_manager.setup_headers()
        print("✅ Google Sheets połączony i gotowy")
    except Exception as e:
        print(f"⚠️ Google Sheets niedostępny: {e}")
        print("ℹ️ Bot będzie działał bez zapisywania danych")
    
    # Inicjalizacja LLM Client (opcjonalne - tylko jeśli skonfigurowane)
    try:
        llm_client = get_llm_client()
        model_info = llm_client.get_model_info()
        print(f"✅ LLM Client połączony: {model_info.get('model_name', 'unknown')}")
    except Exception as e:
        print(f"⚠️ LLM Client niedostępny: {e}")
        print("ℹ️ Bot będzie działał bez funkcji AI")
    
    # Inicjalizacja orkiestratora
    orchestrator = BotOrchestrator(bot, llm_client, sheets_manager)
    
    # Synchronizacja historii czatu z Google Sheets
    if sheets_manager and llm_client:
        print("\n🔄 Rozpoczynam synchronizację historii czatu...")
        await orchestrator.sync_chat_history()



@bot.event
async def on_message(message):
    """Wywoływane gdy bot otrzyma wiadomość."""
    # Ignoruj własne wiadomości
    if message.author == bot.user:
        return
    
    # Przetwarzaj komendy (!)
    await bot.process_commands(message)
    
    # Jeśli wiadomość nie jest komendą i orkiestrator jest dostępny
    if not message.content.startswith('!') and orchestrator:
        await orchestrator.handle_message(message)


@bot.command(name="ping")
async def ping(ctx):
    """Sprawdza czy bot odpowiada."""
    await ctx.send(f"Pong! Latencja: {round(bot.latency * 1000)}ms")


@bot.command(name="hello")
async def hello(ctx):
    """Powitanie od Szczypior Bota."""
    await ctx.send(f"Cześć {ctx.author.mention}! Jestem Szczypior Bot! 🌿")



@bot.command(name="typy_aktywnosci")
async def list_activities(ctx):
    """
    Wyświetla dostępne typy aktywności.
    """
    fields = []
    for activity, info in ACTIVITY_TYPES.items():
        bonuses_text = ", ".join(info['bonuses']) if info['bonuses'] else "brak"
        min_dist_text = f"{info['min_distance']} km" if info['min_distance'] > 0 else "BRAK"
        
        fields.append({
            'name': f"{info['emoji']} {info['display_name']}",
            'value': (
                f"**{info['base_points']} pkt/{info['unit']}**\n"
                f"Min. dystans: {min_dist_text}\n"
                f"Bonusy: {bonuses_text}"
            ),
            'inline': True
        })
    
    embed = create_embed(
        title="🏃 Dostępne typy aktywności",
        description="Lista wszystkich typów aktywności zgodnie z wytycznymi konkursu:",
        color=discord.Color.green(),
        fields=fields,
        footer="Użyj: !dodaj_aktywnosc <typ> <wartość> [obciążenie] [przewyższenie]"
    )
    await ctx.send(embed=embed)


@bot.command(name="dodaj_aktywnosc")
async def add_activity(ctx, activity_type: str, distance: float, 
                       weight: Optional[float] = None, elevation: Optional[float] = None):
    """
    Dodaje nową aktywność.
    
    Przykłady użycia:
    !dodaj_aktywnosc bieganie_teren 5.2
    !dodaj_aktywnosc bieganie_teren 10 5 (z obciążeniem 5kg)
    !dodaj_aktywnosc bieganie_teren 15 0 200 (z przewyższeniem 200m)
    !dodaj_aktywnosc rower 25 0 150
    """
    activity_type = activity_type.lower()
    
    if activity_type not in ACTIVITY_TYPES:
        available = ", ".join([f"`{k}`" for k in ACTIVITY_TYPES.keys()])
        await ctx.send(
            f"❌ Nieznany typ aktywności: `{activity_type}`\n"
            f"Dostępne typy: {available}\n"
            f"Użyj `!typy_aktywnosci` aby zobaczyć szczegóły."
        )
        return
    
    if distance <= 0:
        await ctx.send("❌ Wartość musi być większa niż 0!")
        return
    
    # Oblicz punkty (używamy orkiestratora jeśli dostępny)
    if orchestrator:
        points, error_msg = orchestrator.calculate_points(activity_type, distance, weight, elevation)
    else:
        points, error_msg = 0, "Orkiestrator niedostępny"
    
    if error_msg:
        await ctx.send(f"❌ {error_msg}")
        return
    
    # Zapisz do Google Sheets jeśli dostępny
    info = ACTIVITY_TYPES[activity_type]
    username = get_display_name(ctx.author)
    saved = False
    
    if sheets_manager:
        try:
            # Określ czy jest obciążenie > 5kg
            has_weight = weight is not None and weight > 5
            
            saved = sheets_manager.add_activity(
                username=username,
                activity_type=activity_type,
                distance=distance,
                has_weight=has_weight,
                timestamp=None,
                message_id=str(ctx.message.id),
                message_timestamp=str(ctx.message.created_at.timestamp())
            )
        except Exception as e:
            print(f"Błąd zapisu do Sheets: {e}")
    
    # Przygotuj dodatkowe pola
    additional_fields = []
    if weight and weight > 0:
        additional_fields.append({'name': "Obciążenie", 'value': f"{weight} kg", 'inline': True})
    if elevation and elevation > 0:
        additional_fields.append({'name': "Przewyższenie", 'value': f"{elevation} m", 'inline': True})
    
    # Użyj create_activity_embed z utils
    embed = create_activity_embed(
        activity_info=info,
        username=ctx.author.mention,
        distance=distance,
        points=points,
        additional_fields=additional_fields,
        saved=saved
    )
    
    await ctx.send(embed=embed)


@bot.command(name="moja_historia")
async def my_history(ctx, limit: int = 5):
    """
    Wyświetla ostatnie aktywności użytkownika.
    
    Przykład: !moja_historia 10
    """
    if not sheets_manager:
        await ctx.send("❌ Google Sheets nie jest skonfigurowany. Użyj `!pomoc` aby dowiedzieć się jak go skonfigurować.")
        return
    
    username = get_display_name(ctx.author)
    history = sheets_manager.get_user_history(username)
    
    if not history:
        await ctx.send(f"{ctx.author.mention}, nie masz jeszcze żadnych zapisanych aktywności! Użyj `!dodaj_aktywnosc`")
        return
    
    # Ogranicz do ostatnich N wpisów
    history = history[-limit:][::-1]  # Odwróć aby najnowsze były na górze
    
    fields = []
    for record in history:
        activity = record.get('Aktywność', 'N/A')
        distance = parse_distance(record.get('Dystans (km)', 0))
        points = safe_int(record.get('Punkty', 0))
        date = record.get('Data', 'N/A')
        
        emoji = ACTIVITY_TYPES.get(activity.lower(), {}).get('emoji', '📝')
        fields.append({
            'name': f"{emoji} {activity} - {date}",
            'value': f"Wartość: {distance} | Punkty: {points} 🏆",
            'inline': False
        })
    
    embed = create_embed(
        title=f"📊 Historia aktywności - {ctx.author.display_name}",
        color=discord.Color.blue(),
        fields=fields
    )
    
    await ctx.send(embed=embed)


@bot.command(name="moje_punkty")
async def my_points(ctx):
    """Wyświetla sumę punktów użytkownika."""
    if not sheets_manager:
        await ctx.send("❌ Google Sheets nie jest skonfigurowany.")
        return
    
    username = get_display_name(ctx.author)
    total_points = sheets_manager.get_user_total_points(username)
    history = sheets_manager.get_user_history(username)
    
    embed = create_embed(
        title="🏆 Twoje punkty",
        color=discord.Color.gold(),
        fields=[
            {'name': "Użytkownik", 'value': ctx.author.mention, 'inline': True},
            {'name': "Całkowite punkty", 'value': f"**{total_points}** 🏆", 'inline': True},
            {'name': "Liczba aktywności", 'value': f"{len(history)}", 'inline': True}
        ]
    )
    
    await ctx.send(embed=embed)


@bot.command(name="pomoc")
async def help_command(ctx):
    """Wyświetla listę dostępnych komend."""
    embed = create_embed(
        title="🌿 Szczypior Bot - Pomoc",
        description="Lista dostępnych komend:",
        color=discord.Color.green(),
        fields=[
            {
                'name': "📝 Podstawowe",
                'value': (
                    "`!ping` - Sprawdza latencję bota\n"
                    "`!hello` - Powitanie\n"
                    "`!pomoc` - Ta wiadomość"
                ),
                'inline': False
            },
            {
                'name': "🏃 Aktywności",
                'value': (
                    "`!typy_aktywnosci` - Lista dostępnych aktywności\n"
                    "`!dodaj_aktywnosc <typ> <wartość> [obciążenie] [przewyższenie]` - Dodaj aktywność\n"
                    "`!moja_historia [limit]` - Twoje ostatnie aktywności\n"
                    "`!moje_punkty` - Sprawdź swoje punkty"
                ),
                'inline': False
            },
            {
                'name': "📊 Rankingi i statystyki",
                'value': (
                    "`!ranking [limit]` - Ranking użytkowników według punktów\n"
                    "`!stats` - Statystyki całego serwera\n"
                    "`!stats_aktywnosci` - Najpopularniejsze aktywności"
                ),
                'inline': False
            },
            {
                'name': "📊 Przykłady",
                'value': (
                    "`!dodaj_aktywnosc bieganie_teren 5.2`\n"
                    "`!dodaj_aktywnosc bieganie_teren 10 5` (z 5kg obciążeniem)\n"
                    "`!dodaj_aktywnosc bieganie_teren 15 0 200` (z 200m przewyższeniem)\n"
                    "`!dodaj_aktywnosc rower 25` (rower 25km)\n"
                    "`!moja_historia 10` (ostatnie 10 aktywności)"
                ),
                'inline': False
            }
        ],
        footer="Bot stworzony dla miłośników aktywności fizycznej! 🌿"
    )
    await ctx.send(embed=embed)


@bot.command(name="ranking")
async def ranking(ctx, limit: int = 10):
    """
    Wyświetla ranking użytkowników według punktów.
    
    Przykład: !ranking 5
    """
    if not sheets_manager:
        await ctx.send("❌ Google Sheets nie jest skonfigurowany.")
        return
    
    try:
        # Pobierz wszystkie rekordy i oblicz totalne punkty
        all_records = sheets_manager.worksheet.get_all_records()
        
        if not all_records:
            await ctx.send("📊 Brak danych do wyświetlenia rankingu.")
            return
        
        # Użyj calculate_user_totals z utils
        user_totals = calculate_user_totals(all_records)
        
        # Sortuj według punktów malejąco
        sorted_users = sorted(
            user_totals.items(), 
            key=lambda x: x[1]['total_points'], 
            reverse=True
        )[:limit]
        
        medals = ["🥇", "🥈", "🥉"]
        fields = []
        for i, (username, data) in enumerate(sorted_users):
            medal = medals[i] if i < 3 else f"{i+1}."
            fields.append({
                'name': f"{medal} {username}",
                'value': f"**{data['total_points']}** punktów 🏆",
                'inline': False
            })
        
        embed = create_embed(
            title="🏆 Ranking użytkowników",
            description=f"Top {min(limit, len(sorted_users))} użytkowników według punktów:",
            color=discord.Color.gold(),
            fields=fields
        )
        
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Błąd podczas generowania rankingu: {e}")


@bot.command(name="stats")
async def server_stats(ctx):
    """Wyświetla ogólne statystyki serwera."""
    if not sheets_manager:
        await ctx.send("❌ Google Sheets nie jest skonfigurowany.")
        return
    
    try:
        all_records = sheets_manager.worksheet.get_all_records()
        
        if not all_records:
            await ctx.send("📊 Brak danych do wyświetlenia statystyk.")
            return
        
        # Oblicz statystyki
        total_activities = len(all_records)
        unique_users = len(set(r.get('User', '') for r in all_records if r.get('User')))
        
        # Użyj parse_distance i safe_int z utils
        total_points = sum(safe_int(r.get('Punkty', 0)) for r in all_records)
        total_distance = sum(parse_distance(r.get('Dystans (km)', 0)) for r in all_records)
        
        # Najpopularniejsza aktywność
        activities = [r.get('Aktywność', '') for r in all_records if r.get('Aktywność')]
        if activities:
            from collections import Counter
            most_common = Counter(activities).most_common(1)[0]
            popular_activity = most_common[0]
            popular_count = most_common[1]
        else:
            popular_activity = "N/A"
            popular_count = 0
        
        embed = create_embed(
            title="📊 Statystyki serwera",
            description="Ogólne statystyki wszystkich użytkowników:",
            color=discord.Color.blue(),
            fields=[
                {'name': "👥 Aktywni użytkownicy", 'value': f"**{unique_users}**", 'inline': True},
                {'name': "📝 Liczba aktywności", 'value': f"**{total_activities}**", 'inline': True},
                {'name': "🏆 Suma punktów", 'value': f"**{total_points}**", 'inline': True},
                {'name': "📏 Suma dystansu", 'value': f"**{total_distance:.1f}** km", 'inline': True},
                {'name': "⭐ Najpopularniejsza aktywność", 'value': f"**{popular_activity}** ({popular_count}x)", 'inline': True}
            ]
        )
        
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Błąd podczas generowania statystyk: {e}")


@bot.command(name="stats_aktywnosci")
async def activity_stats(ctx):
    """Wyświetla statystyki według typu aktywności."""
    if not sheets_manager:
        await ctx.send("❌ Google Sheets nie jest skonfigurowany.")
        return
    
    try:
        all_records = sheets_manager.worksheet.get_all_records()
        
        if not all_records:
            await ctx.send("📊 Brak danych do wyświetlenia statystyk.")
            return
        
        # Użyj aggregate_by_field z utils
        activity_stats_data = aggregate_by_field(all_records, 'Aktywność')
        
        # Sortuj według liczby aktywności
        sorted_activities = sorted(
            activity_stats_data.items(),
            key=lambda x: x[1]['count'],
            reverse=True
        )
        
        fields = []
        for activity, stats in sorted_activities:
            info = ACTIVITY_TYPES.get(activity.lower(), {})
            emoji = info.get('emoji', '📝')
            unit = info.get('unit', 'km')
            
            fields.append({
                'name': f"{emoji} {activity.capitalize()}",
                'value': (
                    f"Liczba: **{stats['count']}**\n"
                    f"Suma: **{stats['total_distance']:.1f}** {unit}\n"
                    f"Punkty: **{stats['total_points']}** 🏆"
                ),
                'inline': True
            })
        
        embed = create_embed(
            title="📊 Statystyki aktywności",
            description="Podsumowanie wszystkich typów aktywności:" if sorted_activities else "Brak zapisanych aktywności.",
            color=discord.Color.purple(),
            fields=fields if sorted_activities else None
        )
        
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Błąd podczas generowania statystyk aktywności: {e}")


def main():
    """Główna funkcja uruchamiająca bota."""
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise ValueError("Brak tokena Discord! Ustaw DISCORD_TOKEN w pliku .env")
    bot.run(token)


if __name__ == "__main__":
    main()
