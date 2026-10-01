@echo off
REM Trading bridge — Windows launcher. Edit the three values below once.
cd /d "%~dp0"
set BRIDGE_SECRET=change-me-long-random-text
set BRIDGE_ADMIN_PASS=change-me-too
set BRIDGE_DRY_RUN=1
if not exist accounts.json copy accounts.example.json accounts.json
python -m pip install -q -r requirements.txt
start "" http://127.0.0.1:8000/
python -m uvicorn bridge.server:create_app --factory --host 0.0.0.0 --port 8000
