@echo off
rem Stops Edge Lab running in the background (the server on port 3007).
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":3007" ^| findstr "LISTENING"') do taskkill /PID %%p /F >nul 2>&1 && echo Edge Lab stopped.
timeout /t 2 >nul
