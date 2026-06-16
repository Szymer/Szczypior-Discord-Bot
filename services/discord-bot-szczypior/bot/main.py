"""Szczypior Discord Bot - cienka warstwa transportowa Discord."""

import logging
import os
import sys
from typing import Any

# Upewnij sie, ze sys.path zawiera katalogi potrzebne niezaleznie od CWD/debuggera.
_BOT_DIR = os.path.dirname(os.path.abspath(__file__))
_SVC_DIR = os.path.dirname(_BOT_DIR)
_REPO_ROOT = os.path.dirname(os.path.dirname(_SVC_DIR))
for _path in (_BOT_DIR, _SVC_DIR, _REPO_ROOT):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import discord
from discord.ext import commands
from dotenv import load_dotenv
import asyncio

load_dotenv()

try:
    from bot.message_handler import DiscordMessageHandler, ModuleAIMessageProcessor  # pyright: ignore[reportMissingImports]
except ImportError:
    from message_handler import DiscordMessageHandler, ModuleAIMessageProcessor  # pyright: ignore[reportMissingImports]


class ExtraFormatter(logging.Formatter):
    """Formatter wyswietlajacy pola z extra jako JSON."""

    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        extra_fields = {
            key: value
            for key, value in record.__dict__.items()
            if key
            not in {
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "message",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "thread",
                "threadName",
                "exc_info",
                "exc_text",
                "stack_info",
                "asctime",
            }
        }
        if extra_fields:
            import json

            message += f" | {json.dumps(extra_fields, ensure_ascii=False, default=str)}"
        return message


def _configure_logging() -> logging.Logger:
    formatter = ExtraFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    logging.basicConfig(level=logging.INFO, handlers=[console_handler])
    return logging.getLogger(__name__)


logger = _configure_logging()

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)
message_handler: Any = DiscordMessageHandler(ai_processor=ModuleAIMessageProcessor(), bot=bot)


def register_future_commands() -> None:
    """Placeholder pod przyszle komendy bota."""


@bot.event
async def on_ready() -> None:
    """Wywolywane po poprawnym podlaczeniu bota do Discorda."""
    if bot.user is None:
        logger.warning("Bot connected without resolved user object")
        return

    logger.info("Bot is online", extra={"bot_id": bot.user.id, "bot_name": str(bot.user)})

    api_manager = getattr(message_handler, "_api_manager", None)
    if api_manager is None:
        return

    try:
        challenges = await asyncio.to_thread(api_manager.get_active_challenges)
    except Exception:
        logger.error("Failed to fetch active challenges for startup sync", exc_info=True)
        return

    try:
        await message_handler.sync_active_challenges(challenges)
    except Exception:
        logger.error("Startup sync failed", exc_info=True)


@bot.event
async def on_message(message: discord.Message) -> None:
    """Transportuje wiadomosc Discord do cienkiego handlera."""
    if message.author == bot.user:
        return

    await bot.process_commands(message)

    if message.content.startswith("!"):
        return

    await message_handler.handle(message)


@bot.command(name="ping")
async def ping(ctx: commands.Context) -> None:
    """Sprawdza czy bot odpowiada."""
    await ctx.send(f"Pong! Latencja: {round(bot.latency * 1000)}ms")


async def start() -> None:
    """Uruchamia bota Discord w istniejącej pętli asyncio."""
    register_future_commands()

    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise ValueError("Brak tokena Discord! Ustaw DISCORD_TOKEN w zmiennych środowiskowych")

    await bot.start(token)


def main() -> None:
    """Lokalne uruchomienie bota poza Cloud Run."""
    import asyncio

    asyncio.run(start())


if __name__ == "__main__":
    main()