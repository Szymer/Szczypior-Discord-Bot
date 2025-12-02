"""Szczypior Discord Bot - Główny plik uruchomieniowy."""

import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

# Wczytaj zmienne środowiskowe
load_dotenv()

# Konfiguracja bota
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    """Wywoływane gdy bot jest gotowy."""
    print(f"{bot.user} jest online!")
    print(f"ID bota: {bot.user.id}")


@bot.command(name="ping")
async def ping(ctx):
    """Sprawdza czy bot odpowiada."""
    await ctx.send(f"Pong! Latencja: {round(bot.latency * 1000)}ms")


@bot.command(name="hello")
async def hello(ctx):
    """Powitanie od Szczypior Bota."""
    await ctx.send(f"Cześć {ctx.author.mention}! Jestem Szczypior Bot! 🌿")


def main():
    """Główna funkcja uruchamiająca bota."""
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise ValueError("Brak tokena Discord! Ustaw DISCORD_TOKEN w pliku .env")
    bot.run(token)


if __name__ == "__main__":
    main()
