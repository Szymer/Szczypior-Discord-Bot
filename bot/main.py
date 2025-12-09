"""Szczypior Discord Bot - Główny plik uruchomieniowy."""

import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

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
from .exceptions import ConfigurationError, SheetsError, LLMError

# Wczytaj zmienne środowiskowe
load_dotenv()

# Konfiguracja loggingu
class ExtraFormatter(logging.Formatter):
    """Formatter który wyświetla pola z extra jako JSON."""
    def format(self, record):
        # Pobierz standardowe formatowanie
        message = super().format(record)
        
        # Dodaj pola extra jako JSON (jeśli są)
        extra_fields = {k: v for k, v in record.__dict__.items() 
                       if k not in ['name', 'msg', 'args', 'created', 'filename', 'funcName',
                                   'levelname', 'levelno', 'lineno', 'module', 'msecs',
                                   'message', 'pathname', 'process', 'processName',
                                   'relativeCreated', 'thread', 'threadName', 'exc_info',
                                   'exc_text', 'stack_info', 'asctime']}
        
        if extra_fields:
            import json
            message += f" | {json.dumps(extra_fields, ensure_ascii=False, default=str)}"
        
        return message

formatter = ExtraFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)

file_handler = logging.FileHandler('bot.log', encoding='utf-8')
file_handler.setFormatter(formatter)

logging.basicConfig(
    level=logging.INFO,
    handlers=[console_handler, file_handler]
)
logger = logging.getLogger(__name__)

# Konfiguracja bota
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True
intents.members = True  # Potrzebne do pobierania informacji o członkach
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
    logger.info(f"{bot.user} is online", extra={"bot_id": bot.user.id})
    
    # Inicjalizacja Google Sheets (opcjonalne - tylko jeśli skonfigurowane)
    try:
        sheets_manager = SheetsManager()
        sheets_manager.setup_headers()
        logger.info("Google Sheets connected and ready")
        
        # Buduj cache IID dla szybkiego sprawdzania duplikatów
        sheets_manager.build_iid_cache()
    except Exception as e:
        logger.warning("Google Sheets unavailable", exc_info=True)
        logger.info("Bot will work without data persistence")
    
    # Inicjalizacja LLM Client (opcjonalne - tylko jeśli skonfigurowane)
    try:
        llm_client = get_llm_client()
        model_info = llm_client.get_model_info()
        logger.info("LLM Client connected", extra={"model": model_info.get('model_name', 'unknown')})
    except Exception as e:
        logger.warning("LLM Client unavailable", exc_info=True)
        logger.info("Bot will work without AI functions")
    
    # Inicjalizacja orkiestratora
    orchestrator = BotOrchestrator(bot, llm_client, sheets_manager)
    
    # Synchronizacja historii czatu z Google Sheets
    if sheets_manager and llm_client:
        logger.info("Starting chat history sync")
        await orchestrator.sync_chat_history()
    
    # Synchronizacja komend slash z Discord
    try:
        synced = await bot.tree.sync()
        logger.info("Slash commands synchronized", extra={"count": len(synced)})
    except Exception as e:
        logger.error("Failed to sync slash commands", exc_info=True)



@bot.event
async def on_message(message):
    """Wywoływane gdy bot otrzyma wiadomość."""
    # Ignoruj własne wiadomości
    if message.author == bot.user:
        return
    
    # Filtruj tylko wiadomości z monitorowanego kanału
    monitored_channel_id = os.getenv("MONITORED_CHANNEL_ID")
    if monitored_channel_id and str(message.channel.id) != monitored_channel_id:
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
    actual_points = points  # Domyślnie używamy lokalnie obliczonych punktów
    
    if sheets_manager:
        try:
            # Określ czy jest obciążenie > 5kg
            has_weight = weight is not None and weight > 5
            
            # Stwórz timestamp jako int (zgodnie z formatem IID)
            timestamp_int = int(ctx.message.created_at.timestamp())
            
            saved, row_number = sheets_manager.add_activity(
                username=username,
                activity_type=activity_type,
                distance=distance,
                has_weight=has_weight,
                elevation=elevation,
                timestamp=None,
                message_id=str(ctx.message.id),
                message_timestamp=str(timestamp_int)
            )
            
            # Jeśli zapisano, pobierz punkty z arkusza
            if saved and row_number > 0:
                sheet_points = sheets_manager.get_points_from_row(row_number)
                if sheet_points is not None:
                    actual_points = sheet_points
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
        points=actual_points,
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
        title=f"📊 Historia aktywności - {get_display_name(ctx.author)}",
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


@bot.tree.command(name="podsumowanie", description="Generuje podsumowanie wyników z wybranego okresu z komentarzem AI")
@app_commands.describe(okres="Wybierz okres do podsumowania")
async def podsumowanie(
    interaction: discord.Interaction,
    okres: str
):
    """
    Komenda slash generująca podsumowanie wyników z wybranego okresu.
    
    Args:
        interaction: Interakcja Discord
        okres: Wybrany okres (caly/tydzien/miesiac/ostatni_tydzien)
    """
    await interaction.response.defer(thinking=True)
    
    if not sheets_manager:
        await interaction.followup.send("❌ Google Sheets nie jest skonfigurowany.")
        return
    
    if not llm_client:
        await interaction.followup.send("❌ AI Client nie jest skonfigurowany.")
        return
    
    try:
        # Pobierz wszystkie aktywności
        all_activities = sheets_manager.get_all_activities_with_timestamps()
        
        if not all_activities:
            await interaction.followup.send("📊 Brak danych do podsumowania.")
            return
        
        # Filtruj dane według wybranego okresu
        now = datetime.now()
        filtered_activities = []
        period_title = ""
        
        if okres == "caly":
            filtered_activities = all_activities
            period_title = "Cały konkurs"
        elif okres == "ostatni_tydzien":
            # Ostatni tydzień (niedziela-sobota)
            days_since_sunday = (now.weekday() + 1) % 7
            last_sunday = now - timedelta(days=days_since_sunday + 7)
            last_saturday = last_sunday + timedelta(days=6)
            
            for a in all_activities:
                try:
                    activity_date = datetime.strptime(a['Data'], "%Y-%m-%d %H:%M:%S")
                    if last_sunday <= activity_date <= last_saturday:
                        filtered_activities.append(a)
                except (ValueError, KeyError) as e:
                    logger.warning(f"Błąd parsowania daty dla aktywności: {a.get('Data', 'brak daty')}", exc_info=True)
                    continue
            period_title = f"Ostatni tydzień ({last_sunday.strftime('%d.%m')} - {last_saturday.strftime('%d.%m')})"
        elif okres == "biezacy_tydzien":
            # Bieżący tydzień (od niedzieli do dziś)
            days_since_sunday = (now.weekday() + 1) % 7
            this_sunday = now - timedelta(days=days_since_sunday)
            
            for a in all_activities:
                try:
                    activity_date = datetime.strptime(a['Data'], "%Y-%m-%d %H:%M:%S")
                    if activity_date >= this_sunday:
                        filtered_activities.append(a)
                except (ValueError, KeyError) as e:
                    logger.warning(f"Błąd parsowania daty dla aktywności: {a.get('Data', 'brak daty')}", exc_info=True)
                    continue
            period_title = f"Bieżący tydzień (od {this_sunday.strftime('%d.%m')})"
        elif okres == "miesiac":
            # Ostatni miesiąc kalendarzowy
            if now.month == 1:
                last_month_year = now.year - 1
                last_month = 12
            else:
                last_month_year = now.year
                last_month = now.month - 1
            
            for a in all_activities:
                try:
                    activity_date = datetime.strptime(a['Data'], "%Y-%m-%d %H:%M:%S")
                    if activity_date.month == last_month and activity_date.year == last_month_year:
                        filtered_activities.append(a)
                except (ValueError, KeyError) as e:
                    logger.warning(f"Błąd parsowania daty dla aktywności: {a.get('Data', 'brak daty')}", exc_info=True)
                    continue
            
            month_names = ["Styczeń", "Luty", "Marzec", "Kwiecień", "Maj", "Czerwiec", 
                          "Lipiec", "Sierpień", "Wrzesień", "Październik", "Listopad", "Grudzień"]
            period_title = f"{month_names[last_month - 1]} {last_month_year}"
        
        if not filtered_activities:
            await interaction.followup.send(f"📊 Brak danych dla okresu: {period_title}")
            return
        
        # Oblicz statystyki
        stats = _calculate_period_stats(filtered_activities)
        
        # Wygeneruj komentarz AI
        ai_comment = await _generate_ai_summary(stats, period_title)
        
        # Utwórz embed
        embed = discord.Embed(
            title=f"📊 Podsumowanie: {period_title}",
            description=ai_comment,
            color=discord.Color.gold()
        )
        
        # Dodaj pola statystyk
        embed.add_field(
            name="🏆 Najlepszy wynik",
            value=f"**{stats['top_scorer']['nick']}** - {stats['top_scorer']['punkty']} pkt",
            inline=False
        )
        
        embed.add_field(
            name="🏃 Najdłuższy bieg",
            value=f"**{stats['longest_run']['nick']}** - {stats['longest_run']['dystans']} km ({stats['longest_run']['typ']})",
            inline=False
        )
        
        if stats.get('longest_swim'):
            embed.add_field(
                name="🏊 Najdłuższe pływanie",
                value=f"**{stats['longest_swim']['nick']}** - {stats['longest_swim']['dystans']} km",
                inline=False
            )
        
        embed.add_field(
            name="📈 Łączne statystyki",
            value=(
                f"Aktywności: **{stats['total_activities']}**\n"
                f"Dystans: **{stats['total_distance']:.1f} km**\n"
                f"Punkty: **{stats['total_points']}**"
            ),
            inline=False
        )
        
        embed.add_field(
            name="👥 Aktywni uczestnicy",
            value=f"**{stats['active_users']}** osób",
            inline=True
        )
        
        embed.set_footer(text=f"Wygenerowano: {now.strftime('%Y-%m-%d %H:%M')}")
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Błąd generowania podsumowania: {e}", exc_info=True)
        await interaction.followup.send(f"❌ Wystąpił błąd podczas generowania podsumowania. Spróbuj ponownie.")


@podsumowanie.autocomplete('okres')
async def okres_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[discord.app_commands.Choice[str]]:
    """Autocomplete dla wyboru okresu."""
    choices = [
        discord.app_commands.Choice(name="Cały konkurs", value="caly"),
        discord.app_commands.Choice(name="Bieżący tydzień (niedziela-dziś)", value="biezacy_tydzien"),
        discord.app_commands.Choice(name="Ostatni tydzień (niedziela-sobota)", value="ostatni_tydzien"),
        discord.app_commands.Choice(name="Ostatni miesiąc kalendarzowy", value="miesiac"),
    ]
    return choices


def _calculate_period_stats(activities: list) -> dict:
    """
    Oblicza statystyki dla danego okresu.
    
    Args:
        activities: Lista aktywności z arkusza
        
    Returns:
        Słownik ze statystykami
    """
    from collections import defaultdict
    
    user_points = defaultdict(int)
    user_activities = defaultdict(int)
    longest_run = {'dystans': 0, 'nick': '', 'typ': ''}
    longest_swim = {'dystans': 0, 'nick': ''}
    total_distance = 0
    total_points = 0
    
    for activity in activities:
        nick = activity.get('Nick', 'Nieznany')
        dystans = parse_distance(activity.get('Dystans (km)', 0))
        punkty_str = activity.get('PUNKTY', '0')
        punkty = safe_int(punkty_str)
        typ = activity.get('Rodzaj Aktywności', '')
        
        # Suma punktów użytkownika
        user_points[nick] += punkty
        user_activities[nick] += 1
        
        # Łączne statystyki
        total_distance += dystans
        total_points += punkty
        
        # Najdłuższy bieg (Bieganie teren/bieżnia)
        if 'bieganie' in typ.lower() and dystans > longest_run['dystans']:
            longest_run = {'dystans': dystans, 'nick': nick, 'typ': typ}
        
        # Najdłuższe pływanie
        if 'pływanie' in typ.lower() and dystans > longest_swim['dystans']:
            longest_swim = {'dystans': dystans, 'nick': nick}
    
    # Top scorer
    top_scorer_nick = max(user_points.items(), key=lambda x: x[1])[0] if user_points else ''
    top_scorer_points = user_points[top_scorer_nick] if top_scorer_nick else 0
    
    return {
        'top_scorer': {'nick': top_scorer_nick, 'punkty': top_scorer_points},
        'longest_run': longest_run,
        'longest_swim': longest_swim if longest_swim['dystans'] > 0 else None,
        'total_activities': len(activities),
        'total_distance': total_distance,
        'total_points': total_points,
        'active_users': len(user_points),
        'user_points': dict(user_points),
        'user_activities': dict(user_activities)
    }


async def _generate_ai_summary(stats: dict, period: str) -> str:
    """
    Generuje komentarz AI na podstawie statystyk.
    
    Args:
        stats: Statystyki okresu
        period: Nazwa okresu
        
    Returns:
        Komentarz wygenerowany przez AI
    """
    try:
        # Pobierz prompt z konfiguracji
        from bot.config_manager import config_manager
        provider = config_manager.get_llm_provider()
        prompts = config_manager.get_llm_prompts(provider)
        
        prompt_template = prompts.get("period_summary")
        if not prompt_template:
            # Fallback do starego promptu jeśli nie ma w konfiguracji
            prompt = f"""Wygeneruj krótkie, motywujące podsumowanie aktywności sportowej dla okresu: {period}

STATYSTYKI:
- Łączna liczba aktywności: {stats['total_activities']}
- Łączny dystans: {stats['total_distance']:.1f} km
- Łączne punkty: {stats['total_points']}
- Liczba aktywnych uczestników: {stats['active_users']}
- Najlepszy wynik: {stats['top_scorer']['nick']} ({stats['top_scorer']['punkty']} pkt)
- Najdłuższy bieg: {stats['longest_run']['nick']} ({stats['longest_run']['dystans']} km, {stats['longest_run']['typ']})
{f"- Najdłuższe pływanie: {stats['longest_swim']['nick']} ({stats['longest_swim']['dystans']} km)" if stats.get('longest_swim') else ""}

WYMAGANIA:
1. Podsumowanie powinno być krótkie (2-4 zdania)
2. Ton entuzjastyczny i motywujący
3. Doceniaj osiągnięcia uczestników
4. Zwróć uwagę na ciekawe fakty (np. największy dystans, najwięcej punktów)
5. Użyj emoji dla emocji (max 2-3)
6. NIE używaj markdown (bez **bold**, _italic_, itp.)

Wygeneruj tylko tekst podsumowania, bez dodatkowych komentarzy."""
        else:
            # Przygotuj tekst dla najdłuższego pływania
            longest_swim_text = ""
            if stats.get('longest_swim'):
                longest_swim_text = f"- Najdłuższe pływanie: {stats['longest_swim']['nick']} ({stats['longest_swim']['dystans']} km)"
            
            # Wypełnij szablon promptu
            prompt = prompt_template.format(
                period=period,
                total_activities=stats['total_activities'],
                total_distance=f"{stats['total_distance']:.1f}",
                total_points=stats['total_points'],
                active_users=stats['active_users'],
                top_scorer_nick=stats['top_scorer']['nick'],
                top_scorer_points=stats['top_scorer']['punkty'],
                longest_run_nick=stats['longest_run']['nick'],
                longest_run_distance=stats['longest_run']['dystans'],
                longest_run_type=stats['longest_run']['typ'],
                longest_swim_text=longest_swim_text
            )

        # Pobierz globalny system_prompt
        system_prompt = config_manager.get_system_prompt(provider)
        
        response = await llm_client.generate_text(prompt, system_instruction=system_prompt)
        
        if response:
            # Usuń markdown formatting jeśli AI je dodało
            response = response.replace('**', '').replace('__', '').replace('*', '').replace('_', '')
            return response
        
        return f"Świetna robota! W okresie '{period}' zrealizowano {stats['total_activities']} aktywności na łączny dystans {stats['total_distance']:.1f} km! 🎉"
        
    except Exception as e:
        logger.error(f"Błąd generowania komentarza AI: {e}", exc_info=True)
        return f"Imponujące wyniki w okresie '{period}'! Łącznie {stats['total_activities']} aktywności i {stats['total_points']} punktów! 💪"


def main():
    """Główna funkcja uruchamiająca bota."""
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise ValueError("Brak tokena Discord! Ustaw DISCORD_TOKEN w pliku .env")
    bot.run(token)


if __name__ == "__main__":
    main()
