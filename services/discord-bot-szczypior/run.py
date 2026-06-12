"""Punkt wejsciowy bota. Uruchamiac z katalogu discord-bot-szczypior/.

Ustawia sys.path tak, zeby pakiety 'ai', 'bot' i 'config' byly widoczne
bez wzgledu na to, z jakiego katalogu zostanie wywolany skrypt.
"""

import os
import sys

# Katalog zawierajacy ten plik (discord-bot-szczypior/) jako root
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
BOT_DIR = os.path.join(ROOT_DIR, "bot")
REPO_ROOT = os.path.join(ROOT_DIR, "..", "..")  # /workspaces/Szczypior-Discord-Bot/

for path in (ROOT_DIR, BOT_DIR, os.path.abspath(REPO_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

# Import i uruchomienie po poprawnym ustawieniu sciezek
import main  # noqa: E402  (bot/main.py)
