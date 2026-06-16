"""Punkt wejściowy bota na Cloud Run.

Uruchamia:
1. HTTP health server wymagany przez Cloud Run,
2. Discord bota.
"""

import asyncio
import os
import sys

from aiohttp import web

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
BOT_DIR = os.path.join(ROOT_DIR, "bot")
REPO_ROOT = os.path.abspath(os.path.join(ROOT_DIR, "..", ".."))

for path in (ROOT_DIR, BOT_DIR, REPO_ROOT):
    if path not in sys.path:
        sys.path.insert(0, path)


async def health(request: web.Request) -> web.Response:
    return web.Response(text="ok")


async def start_health_server() -> None:
    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)

    port = int(os.environ.get("PORT", "8080"))

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, host="0.0.0.0", port=port)
    await site.start()

    print(f"Health server started on 0.0.0.0:{port}", flush=True)


async def main_entrypoint() -> None:
    await start_health_server()

    import main  # importuje bot/main.py dzięki sys.path

    await main.start()


if __name__ == "__main__":
    asyncio.run(main_entrypoint())
