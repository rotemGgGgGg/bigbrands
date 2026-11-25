@echo off
rem Double-click to update and start Edge Lab, then open it in the browser.
title Edge Lab
cd /d "%~dp0"
echo Updating Edge Lab...
git pull
echo.
echo Starting Edge Lab. Keep this window open while you use it.
start "" /b cmd /c "timeout /t 3 >nul & start http://localhost:3007"
npm start
pause
