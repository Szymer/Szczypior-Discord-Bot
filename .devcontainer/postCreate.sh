#!/bin/sh
set -eu

cd /workspaces/Szczypior-Discord-Bot

python -m pip install --upgrade pip
python -m pip install -r services/discord-bot-szczypior/requirements.txt
python -m pip install -r services/db-service/requirements.txt

echo "Devcontainer setup complete."
