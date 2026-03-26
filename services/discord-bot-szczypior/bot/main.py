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

from api_menager import APIManager, APIManagerError, APIManagerHTTPError
from constants import ACTIVITY_TYPES
from llm_clients import get_llm_client
from orchestrator import BotOrchestrator
from utils import (
    get_display_name,
    create_embed,
    parse_distance,
    safe_int,
)

# Wczytaj zmienne środowiskowe
load_dotenv()

# Konfiguracja loggingu
class ExtraFormatter(logging.Formatter):
    """Formatter który wyświetla pola z extra jako JSON."""
    def format(self, record):
        message = super().format(record)
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
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Globalny APIManager
api_manager: Optional[APIManager] = None

# Klient LLM
llm_client = None

# Orkiestrator
orchestrator = None

# Zestaw monitorowanych kanałów (ID jako stringi) – wczytany z aktywnych eventów
monitored_channel_ids: set[str] = set()

# Mapa kanał -> challenge_id (wczytana z aktywnych challenge'y)
channel_to_challenge: dict[str, int] = {}

# Jednorazowy startup sync backlogu wiadomości dla aktywnych challenge'y
startup_sync_completed = False


@bot.event
async def on_ready():
    """Wywoływane gdy bot jest gotowy."""
    global api_manager, llm_client, orchestrator, monitored_channel_ids, channel_to_challenge, startup_sync_completed
    logger.info(f"{bot.user} is online", extra={"bot_id": bot.user.id})
    active_challenges = []

    # Monitor pamięci - START
    try:
        import psutil
        import os as os_module
        process = psutil.Process(os_module.getpid())
        mem_start = process.memory_info()
        logger.info(f"🔍 MEMORY START: RSS={mem_start.rss/1024/1024:.2f} MB, VMS={mem_start.vms/1024/1024:.2f} MB")
    except ImportError:
        logger.warning("psutil not installed - memory monitoring disabled")
        process = None

    # Inicjalizacja APIManager
    try:
        api_manager = APIManager()
        logger.info("APIManager initialized", extra={"base_url": api_manager.api_base_url})
    except Exception:
        logger.error("Failed to initialize APIManager", exc_info=True)
        api_manager = None

    # --- Pobierz aktywne challenge'e i ustal kanały do monitorowania ---
    # Debug override: CHALLENGE_ID wymusza jeden konkretny challenge dla wszystkich kanałów
    debug_challenge_id = os.getenv("CHALLENGE_ID", "").strip()

    # Debug override: MONITORED_CHANNEL_ID wymusza jeden konkretny kanał
    debug_channel_override = os.getenv("MONITORED_CHANNEL_ID", "").strip()

    if api_manager:
        try:
            active_challenges = api_manager.get_active_challenges()
            # Zbuduj mapę kanał -> challenge_id
            for ch in active_challenges:
                if ch.discord_channel_id:
                    channel_to_challenge[ch.discord_channel_id] = ch.id
            logger.info(
                "Loaded active challenges",
                extra={
                    "challenge_count": len(active_challenges),
                    "channel_to_challenge": channel_to_challenge,
                }
            )
        except APIManagerError:
            logger.warning("Could not fetch active challenges from API", exc_info=True)

    # Debug override challenge_id – nadpisuje mapowanie for all channels
    if debug_challenge_id:
        try:
            debug_challenge_int = int(debug_challenge_id)
            for ch_id in list(channel_to_challenge.keys()):
                channel_to_challenge[ch_id] = debug_challenge_int
            logger.warning(
                "DEBUG OVERRIDE: forcing challenge_id for all channels",
                extra={"challenge_id": debug_challenge_int}
            )
        except ValueError:
            logger.error(f"Invalid CHALLENGE_ID env value: {debug_challenge_id!r}")

    # Ustal monitorowane kanały: ze schedy challenge'y + debug override
    if debug_channel_override and debug_channel_override != "your_channel_id_here":
        monitored_channel_ids = {debug_channel_override}
        # Jeśli jest debug override kanału + debug override challenge, dodaj do mapy
        if debug_challenge_id:
            try:
                channel_to_challenge[debug_channel_override] = int(debug_challenge_id)
            except ValueError:
                pass
        logger.warning(
            "DEBUG OVERRIDE: monitoring single channel from env",
            extra={"channel_id": debug_channel_override}
        )
    else:
        monitored_channel_ids = set(channel_to_challenge.keys())

    if not monitored_channel_ids:
        logger.warning("No monitored channels configured – bot will process ALL channels")

    # Inicjalizacja LLM Client
    try:
        llm_client = get_llm_client()
        model_info = llm_client.get_model_info()
        logger.info("LLM Client connected", extra={"model": model_info.get('model_name', 'unknown')})
    except Exception:
        logger.warning("LLM Client unavailable", exc_info=True)

    # Inicjalizacja orkiestratora
    orchestrator = BotOrchestrator(bot, llm_client, api_manager)

    # Monitor pamięci - PO INICJALIZACJI
    if process:
        mem_after_init = process.memory_info()
        logger.info(f"🔍 MEMORY AFTER INIT: RSS={mem_after_init.rss/1024/1024:.2f} MB (Δ {(mem_after_init.rss-mem_start.rss)/1024/1024:.2f} MB)")

    # Synchronizacja komend slash z Discord
    try:
        synced = await bot.tree.sync()
        logger.info("Slash commands synchronized", extra={"count": len(synced)})
    except Exception:
        logger.error("Failed to sync slash commands", exc_info=True)

    if orchestrator and not startup_sync_completed:
        try:
            startup_sync_summary = await orchestrator.sync_active_challenges(active_challenges)
            startup_sync_completed = True
            logger.info("Startup challenge sync finished", extra=startup_sync_summary)
        except Exception:
            logger.error("Startup challenge sync failed", exc_info=True)


@bot.event
async def on_message(message):
    """Wywoływane gdy bot otrzyma wiadomość."""
    if message.author == bot.user:
        return

    # Filtr kanałów – jeśli lista nie jest pusta, przepuszczamy tylko skonfigurowane kanały
    if monitored_channel_ids and str(message.channel.id) not in monitored_channel_ids:
        return

    # Przetwarzaj komendy (!)
    await bot.process_commands(message)

    # Jeśli wiadomość nie jest komendą i orkiestrator jest dostępny
    if not message.content.startswith('!') and orchestrator:
        await orchestrator.handle_message(message)


# ── Komendy podstawowe ─────────────────────────────────────────────────────

@bot.command(name="ping")
async def ping(ctx):
    """Sprawdza czy bot odpowiada."""
    await ctx.send(f"Pong! Latencja: {round(bot.latency * 1000)}ms")


@bot.command(name="hello")
async def hello(ctx):
    """Powitanie od Szczypior Bota."""
    await ctx.send(f"Cześć {ctx.author.mention}! Jestem Szczypior Bot! 🌿")


# ── Komendy aktywności ─────────────────────────────────────────────────────

@bot.command(name="moja_historia")
async def my_history(ctx, limit: int = 5):
    """
    Wyświetla ostatnie aktywności użytkownika.

    Przykład: !moja_historia 10
    """
    if not api_manager:
        await ctx.send("❌ API nie jest dostępne.")
        return

    try:
        history = api_manager.get_user_activities(str(ctx.author.id), limit=limit)
    except APIManagerError as e:
        await ctx.send(f"❌ Błąd pobierania historii: {e}")
        return

    if not history:
        await ctx.send(f"{ctx.author.mention}, nie masz jeszcze żadnych zapisanych aktywności!")
        return

    fields = []
    for act in history:
        emoji = ACTIVITY_TYPES.get(act.activity_type, {}).get('emoji', '📝')
        fields.append({
            'name': f"{emoji} {act.activity_type} - {act.created_at.strftime('%Y-%m-%d')}",
            'value': f"Dystans: {act.distance_km} km | Punkty: {act.total_points} 🏆",
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
    if not api_manager:
        await ctx.send("❌ API nie jest dostępne.")
        return

    try:
        history = api_manager.get_user_activities(str(ctx.author.id), limit=200)
    except APIManagerError as e:
        await ctx.send(f"❌ Błąd pobierania danych: {e}")
        return

    total_points = sum(act.total_points for act in history)

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


@bot.command(name="ranking")
async def ranking(ctx, limit: int = 10):
    """
    Wyświetla ranking użytkowników według punktów.

    Przykład: !ranking 5
    """
    if not api_manager:
        await ctx.send("❌ API nie jest dostępne.")
        return

    try:
        top_users = api_manager.get_rankings(limit=limit)
    except APIManagerError as e:
        await ctx.send(f"❌ Błąd pobierania rankingu: {e}")
        return

    if not top_users:
        await ctx.send("📊 Brak danych do wyświetlenia rankingu.")
        return

    medals = ["🥇", "🥈", "🥉"]
    fields = []
    for i, user in enumerate(top_users):
        medal = medals[i] if i < 3 else f"{i+1}."
        fields.append({
            'name': f"{medal} {user.display_name}",
            'value': f"**{user.total_points}** punktów 🏆 | {user.total_activities} aktywności",
            'inline': False
        })

    embed = create_embed(
        title="🏆 Ranking użytkowników",
        description=f"Top {len(top_users)} według punktów:",
        color=discord.Color.gold(),
        fields=fields
    )
    await ctx.send(embed=embed)


@bot.command(name="activity_fix")
async def activity_fix(ctx, activity_type: str, weight_kg: Optional[float] = None, elevation_m: Optional[int] = None):
    """
    Poprawia błędnie rozpoznaną aktywność (tylko admini).
    Użycie: odpowiedz na wiadomość bota komendą
      !activity_fix <typ_aktywnosci> [obciazenie_kg] [przewyzszenie_m]

    Przykłady:
      !activity_fix bieganie_teren
      !activity_fix bieganie_teren 5
      !activity_fix bieganie_teren 0 200
    """
    # Sprawdź uprawnienia – musi być administrator lub manage_messages
    if not (ctx.author.guild_permissions.administrator or ctx.author.guild_permissions.manage_messages):
        await ctx.send("❌ Brak uprawnień. Komenda dostępna tylko dla adminów.")
        return

    if not api_manager:
        await ctx.send("❌ API nie jest dostępne.")
        return

    # Sprawdź czy to odpowiedź na wiadomość
    if not ctx.message.reference:
        await ctx.send("❌ Użyj tej komendy odpowiadając na wiadomość bota z rozpoznaną aktywnością.")
        return

    # Pobierz wiadomość, na którą odpowiada admin
    try:
        ref_msg = ctx.message.reference.resolved
        if ref_msg is None:
            ref_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
    except (discord.NotFound, discord.HTTPException):
        await ctx.send("❌ Nie można pobrać oryginalnej wiadomości.")
        return

    # Sprawdź czy to wiadomość bota
    if ref_msg.author != bot.user:
        await ctx.send("❌ Możesz poprawiać tylko wiadomości wysłane przez bota.")
        return

    # Wyciągnij IID z footera embeda
    iid = None
    if ref_msg.embeds:
        footer = ref_msg.embeds[0].footer
        if footer and footer.text and footer.text.startswith("IID:"):
            iid_part = footer.text.split("|")[0].strip()
            iid = iid_part.replace("IID:", "").strip()

    if not iid:
        await ctx.send("❌ Nie znaleziono IID aktywności w tej wiadomości. Upewnij się, że odpowiadasz na oryginalną odpowiedź bota.")
        return

    # Walidacja nowego typu aktywności
    if activity_type not in ACTIVITY_TYPES:
        valid_types = ", ".join(ACTIVITY_TYPES.keys())
        await ctx.send(f"❌ Nieznany typ aktywności: `{activity_type}`\nDostępne: {valid_types}")
        return

    # Pobierz aktualną aktywność
    try:
        current = api_manager.get_activity(iid)
    except APIManagerHTTPError as e:
        if e.status_code == 404:
            await ctx.send(f"❌ Aktywność o IID `{iid}` nie została znaleziona.")
        else:
            await ctx.send(f"❌ Błąd API: {e.detail}")
        return
    except APIManagerError as e:
        await ctx.send(f"❌ Błąd połączenia: {e}")
        return

    # Przelicz punkty z nowymi danymi
    distance = current.distance_km
    breakdown, calc_error = orchestrator.calculate_points_breakdown(
        activity_type=activity_type,
        distance=distance,
        weight=weight_kg,
        elevation=elevation_m,
        challenge_id=current.challenge_id,
    )
    if calc_error:
        await ctx.send(f"❌ Nie udało się przeliczyć punktów: {calc_error}")
        return

    base_pts = breakdown["base_points"]
    w_bonus = breakdown["weight_bonus_points"]
    e_bonus = breakdown["elevation_bonus_points"]
    new_total = breakdown["total_points"]

    # Wyślij update do API
    from libs.shared.schemas.activity import ActivityUpdate
    payload = ActivityUpdate(
        activity_type=activity_type,
        weight_kg=weight_kg,
        elevation_m=elevation_m,
        weight_bonus_points=w_bonus,
        elevation_bonus_points=e_bonus,
        total_points=new_total,
    )

    try:
        updated = api_manager.update_activity(iid, payload)
    except APIManagerHTTPError as e:
        await ctx.send(f"❌ Błąd aktualizacji: {e.detail}")
        return
    except APIManagerError as e:
        await ctx.send(f"❌ Błąd połączenia: {e}")
        return

    info = ACTIVITY_TYPES[updated.activity_type]
    embed = discord.Embed(
        title=f"✅ Aktywność poprawiona",
        color=discord.Color.green(),
    )
    embed.add_field(name="IID", value=f"`{updated.iid}`", inline=False)
    embed.add_field(name="Nowy typ", value=f"{info['emoji']} {info['display_name']}", inline=True)
    embed.add_field(name="Dystans", value=f"{updated.distance_km} km", inline=True)
    if weight_kg:
        embed.add_field(name="🎒 Obciążenie", value=f"{weight_kg} kg", inline=True)
    if elevation_m:
        embed.add_field(name="⛰️ Przewyższenie", value=f"{elevation_m} m", inline=True)
    embed.add_field(name="🏆 Nowe punkty", value=f"**{updated.total_points}**", inline=False)
    embed.set_footer(text=f"Poprawiono przez {get_display_name(ctx.author)}")
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
                    "`!moja_historia [limit]` - Twoje ostatnie aktywności\n"
                    "`!moje_punkty` - Sprawdź swoje punkty"
                ),
                'inline': False
            },
            {
                'name': "📊 Rankingi",
                'value': "`!ranking [limit]` - Ranking użytkowników według punktów",
                'inline': False
            },
            {
                'name': "🔧 Admin",
                'value': (
                    "`!activity_fix <typ> [obciazenie_kg] [przewyzszenie_m]` - "
                    "Odpowiedz na wiadomość bota, aby poprawić rozpoznaną aktywność"
                ),
                'inline': False
            },
        ],
        footer="Bot stworzony dla miłośników aktywności fizycznej! 🌿"
    )
    await ctx.send(embed=embed)


# ── Komendy slash ──────────────────────────────────────────────────────────

@bot.tree.command(name="podsumowanie", description="Generuje podsumowanie wyników z wybranego okresu z komentarzem AI")
@app_commands.describe(okres="Wybierz okres do podsumowania")
async def podsumowanie(
    interaction: discord.Interaction,
    okres: str
):
    await interaction.response.defer(thinking=True)

    if not api_manager:
        await interaction.followup.send("❌ API nie jest dostępne.")
        return

    if not llm_client:
        await interaction.followup.send("❌ AI Client nie jest skonfigurowany.")
        return

    try:
        top_users = api_manager.get_rankings(limit=10)
    except APIManagerError as e:
        await interaction.followup.send(f"❌ Błąd pobierania rankingu: {e}")
        return

    if not top_users:
        await interaction.followup.send("📊 Brak danych do podsumowania.")
        return

    period_names = {
        "caly": "Cały konkurs",
        "biezacy_tydzien": "Bieżący tydzień",
        "ostatni_tydzien": "Ostatni tydzień",
        "miesiac": "Ostatni miesiąc",
    }
    period_title = period_names.get(okres, okres)

    total_points = sum(u.total_points for u in top_users)
    total_activities = sum(u.total_activities for u in top_users)
    total_distance = sum(u.total_distance_km for u in top_users)
    top_scorer = top_users[0] if top_users else None

    ai_comment = await _generate_ai_summary_from_rankings(top_users, period_title)

    embed = discord.Embed(
        title=f"📊 Podsumowanie: {period_title}",
        description=ai_comment,
        color=discord.Color.gold()
    )

    if top_scorer:
        embed.add_field(
            name="🏆 Lider",
            value=f"**{top_scorer.display_name}** - {top_scorer.total_points} pkt",
            inline=False
        )

    embed.add_field(
        name="📈 Łączne statystyki (top 10)",
        value=(
            f"Aktywności: **{total_activities}**\n"
            f"Dystans: **{total_distance:.1f} km**\n"
            f"Punkty: **{total_points}**"
        ),
        inline=False
    )
    embed.set_footer(text=f"Wygenerowano: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    await interaction.followup.send(embed=embed)


@podsumowanie.autocomplete('okres')
async def okres_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[discord.app_commands.Choice[str]]:
    choices = [
        discord.app_commands.Choice(name="Cały konkurs", value="caly"),
        discord.app_commands.Choice(name="Bieżący tydzień", value="biezacy_tydzien"),
        discord.app_commands.Choice(name="Ostatni tydzień", value="ostatni_tydzien"),
        discord.app_commands.Choice(name="Ostatni miesiąc", value="miesiac"),
    ]
    return choices


async def _generate_ai_summary_from_rankings(top_users, period: str) -> str:
    try:
        from .config_manager import config_manager
        provider = config_manager.get_llm_provider()
        system_prompt = config_manager.get_system_prompt(provider)

        top_lines = "\n".join(
            f"{i+1}. {u.display_name}: {u.total_points} pkt, {u.total_activities} aktywności, {u.total_distance_km:.1f} km"
            for i, u in enumerate(top_users[:5])
        )
        prompt = (
            f"Wygeneruj krótkie (2-3 zdania), motywujące podsumowanie dla okresu: {period}\n\n"
            f"TOP UŻYTKOWNICY:\n{top_lines}\n\n"
            "Ton entuzjastyczny, max 2 emoji, bez markdown."
        )

        response = llm_client.generate_text(prompt, system_instruction=system_prompt)
        if response:
            return response.replace('**', '').replace('__', '').replace('*', '')
    except Exception:
        logger.error("Failed to generate AI summary", exc_info=True)

    leader = top_users[0].display_name if top_users else "N/A"
    return f"Świetne wyniki w {period}! Lider: {leader} 💪"


def main():
    """Główna funkcja uruchamiająca bota."""
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise ValueError("Brak tokena Discord! Ustaw DISCORD_TOKEN w pliku .env")
    bot.run(token)


if __name__ == "__main__":
    main()
