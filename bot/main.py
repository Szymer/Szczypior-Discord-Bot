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
    """Wyświetla dostępne typy aktywności."""
    embed = discord.Embed(
        title="🏃 Dostępne typy aktywności",
        description="Lista wszystkich typów aktywności zgodnie z wytycznymi konkursu:",
        color=discord.Color.green()
    )
    
    for activity, info in ACTIVITY_TYPES.items():
        bonuses_text = ", ".join(info['bonuses']) if info['bonuses'] else "brak"
        min_dist_text = f"{info['min_distance']} km" if info['min_distance'] > 0 else "BRAK"
        
        embed.add_field(
            name=f"{info['emoji']} {info['display_name']}",
            value=(
                f"**{info['base_points']} pkt/{info['unit']}**\n"
                f"Min. dystans: {min_dist_text}\n"
                f"Bonusy: {bonuses_text}"
            ),
            inline=True
        )
    
    embed.set_footer(text="Użyj: !dodaj_aktywnosc <typ> <wartość> [obciążenie] [przewyższenie]")
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
    username = str(ctx.author)
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
    
    # Przygotuj odpowiedź
    info = ACTIVITY_TYPES[activity_type]
    embed = discord.Embed(
        title=f"{info['emoji']} Aktywność dodana!",
        color=discord.Color.green() if saved else discord.Color.orange()
    )
    
    embed.add_field(name="Użytkownik", value=ctx.author.mention, inline=True)
    embed.add_field(name="Typ", value=info['display_name'], inline=True)
    embed.add_field(name=f"Dystans ({info['unit']})", value=f"{distance}", inline=True)
    
    if weight and weight > 0:
        embed.add_field(name="Obciążenie", value=f"{weight} kg", inline=True)
    if elevation and elevation > 0:
        embed.add_field(name="Przewyższenie", value=f"{elevation} m", inline=True)
    
    embed.add_field(name="Punkty", value=f"🏆 **{points}**", inline=False)
    
    if not saved:
        embed.set_footer(text="⚠️ Dane nie zostały zapisane do Google Sheets")
    
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
    
    username = str(ctx.author)
    history = sheets_manager.get_user_history(username)
    
    if not history:
        await ctx.send(f"{ctx.author.mention}, nie masz jeszcze żadnych zapisanych aktywności! Użyj `!dodaj_aktywnosc`")
        return
    
    # Ogranicz do ostatnich N wpisów
    history = history[-limit:][::-1]  # Odwróć aby najnowsze były na górze
    
    embed = discord.Embed(
        title=f"📊 Historia aktywności - {ctx.author.display_name}",
        color=discord.Color.blue()
    )
    
    for record in history:
        activity = record.get('Aktywność', 'N/A')
        distance = record.get('Dystans (km)', 0)
        points = record.get('Punkty', 0)
        date = record.get('Data', 'N/A')
        
        emoji = ACTIVITY_TYPES.get(activity.lower(), {}).get('emoji', '📝')
        embed.add_field(
            name=f"{emoji} {activity} - {date}",
            value=f"Wartość: {distance} | Punkty: {points} 🏆",
            inline=False
        )
    
    await ctx.send(embed=embed)


@bot.command(name="moje_punkty")
async def my_points(ctx):
    """Wyświetla sumę punktów użytkownika."""
    if not sheets_manager:
        await ctx.send("❌ Google Sheets nie jest skonfigurowany.")
        return
    
    username = str(ctx.author)
    total_points = sheets_manager.get_user_total_points(username)
    history = sheets_manager.get_user_history(username)
    
    embed = discord.Embed(
        title=f"🏆 Twoje punkty",
        color=discord.Color.gold()
    )
    
    embed.add_field(name="Użytkownik", value=ctx.author.mention, inline=True)
    embed.add_field(name="Całkowite punkty", value=f"**{total_points}** 🏆", inline=True)
    embed.add_field(name="Liczba aktywności", value=f"{len(history)}", inline=True)
    
    await ctx.send(embed=embed)


@bot.command(name="pomoc")
async def help_command(ctx):
    """Wyświetla listę dostępnych komend."""
    embed = discord.Embed(
        title="🌿 Szczypior Bot - Pomoc",
        description="Lista dostępnych komend:",
        color=discord.Color.green()
    )
    
    embed.add_field(
        name="📝 Podstawowe",
        value=(
            "`!ping` - Sprawdza latencję bota\n"
            "`!hello` - Powitanie\n"
            "`!pomoc` - Ta wiadomość"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🏃 Aktywności",
        value=(
            "`!typy_aktywnosci` - Lista dostępnych aktywności\n"
            "`!dodaj_aktywnosc <typ> <wartość> [obciążenie] [przewyższenie]` - Dodaj aktywność\n"
            "`!moja_historia [limit]` - Twoje ostatnie aktywności\n"
            "`!moje_punkty` - Sprawdź swoje punkty"
        ),
        inline=False
    )
    
    embed.add_field(
        name="📊 Rankingi i statystyki",
        value=(
            "`!ranking [limit]` - Ranking użytkowników według punktów\n"
            "`!stats` - Statystyki całego serwera\n"
            "`!stats_aktywnosci` - Najpopularniejsze aktywności"
        ),
        inline=False
    )
    
    embed.add_field(
        name="📊 Przykłady",
        value=(
            "`!dodaj_aktywnosc bieganie_teren 5.2`\n"
            "`!dodaj_aktywnosc bieganie_teren 10 5` (z 5kg obciążeniem)\n"
            "`!dodaj_aktywnosc bieganie_teren 15 0 200` (z 200m przewyższeniem)\n"
            "`!dodaj_aktywnosc rower 25` (rower 25km)\n"
            "`!moja_historia 10` (ostatnie 10 aktywności)"
        ),
        inline=False
    )
    
    embed.set_footer(text="Bot stworzony dla miłośników aktywności fizycznej! 🌿")
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
        # Pobierz wszystkie rekordy
        all_records = sheets_manager.worksheet.get_all_records()
        
        if not all_records:
            await ctx.send("📊 Brak danych do wyświetlenia rankingu.")
            return
        
        # Oblicz punkty dla każdego użytkownika
        user_points = {}
        for record in all_records:
            username = record.get('User', '')
            points = record.get('Punkty', 0)
            if username:
                user_points[username] = user_points.get(username, 0) + points
        
        # Sortuj według punktów malejąco
        sorted_users = sorted(user_points.items(), key=lambda x: x[1], reverse=True)
        sorted_users = sorted_users[:limit]
        
        embed = discord.Embed(
            title="🏆 Ranking użytkowników",
            description=f"Top {min(limit, len(sorted_users))} użytkowników według punktów:",
            color=discord.Color.gold()
        )
        
        medals = ["🥇", "🥈", "🥉"]
        for i, (username, points) in enumerate(sorted_users):
            medal = medals[i] if i < 3 else f"{i+1}."
            embed.add_field(
                name=f"{medal} {username}",
                value=f"**{points}** punktów 🏆",
                inline=False
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
        total_points = sum(r.get('Punkty', 0) for r in all_records)
        total_distance = sum(r.get('Dystans (km)', 0) for r in all_records)
        
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
        
        embed = discord.Embed(
            title="📊 Statystyki serwera",
            description="Ogólne statystyki wszystkich użytkowników:",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="👥 Aktywni użytkownicy", value=f"**{unique_users}**", inline=True)
        embed.add_field(name="📝 Liczba aktywności", value=f"**{total_activities}**", inline=True)
        embed.add_field(name="🏆 Suma punktów", value=f"**{total_points}**", inline=True)
        embed.add_field(name="📏 Suma dystansu", value=f"**{total_distance:.1f}** km", inline=True)
        embed.add_field(
            name="⭐ Najpopularniejsza aktywność",
            value=f"**{popular_activity}** ({popular_count}x)",
            inline=True
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
        
        # Grupuj według typu aktywności
        activity_stats = {}
        for record in all_records:
            activity = record.get('Aktywność', '').lower()
            if activity and activity in ACTIVITY_TYPES:
                if activity not in activity_stats:
                    activity_stats[activity] = {
                        'count': 0,
                        'total_distance': 0,
                        'total_points': 0
                    }
                activity_stats[activity]['count'] += 1
                activity_stats[activity]['total_distance'] += record.get('Dystans (km)', 0)
                activity_stats[activity]['total_points'] += record.get('Punkty', 0)
        
        # Sortuj według liczby aktywności
        sorted_activities = sorted(
            activity_stats.items(),
            key=lambda x: x[1]['count'],
            reverse=True
        )
        
        embed = discord.Embed(
            title="📊 Statystyki aktywności",
            description="Podsumowanie wszystkich typów aktywności:",
            color=discord.Color.purple()
        )
        
        for activity, stats in sorted_activities:
            info = ACTIVITY_TYPES.get(activity, {})
            emoji = info.get('emoji', '📝')
            embed.add_field(
                name=f"{emoji} {activity.capitalize()}",
                value=(
                    f"Liczba: **{stats['count']}**\n"
                    f"Suma: **{stats['total_distance']:.1f}** {info.get('unit', 'km')}\n"
                    f"Punkty: **{stats['total_points']}** 🏆"
                ),
                inline=True
            )
        
        if not sorted_activities:
            embed.description = "Brak zapisanych aktywności."
        
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
