# Helper script to run tests and ruff in PowerShell
python -m pip install -r requirements-dev.txt -r requirements.txt
ruff check . || exit $LASTEXITCODE
pytest -q --disable-warnings
