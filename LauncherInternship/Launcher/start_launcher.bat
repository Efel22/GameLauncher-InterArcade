@echo off
setlocal

rem Folder this script lives in - resolved automatically so this works no
rem matter where it's placed on the arcade PC, no path to edit.
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

:loop
echo [%date% %time%] Starting launcher_server.py... >> launcher_log.txt

rem pythonw runs without popping its own console window. If "pythonw" isn't
rem recognized, change this to "python" (you'll get a small console box too,
rem but it'll still work). launcher_server.py serves launcher.html, opens
rem Chrome in kiosk mode, and handles /launch requests to start games.
pythonw "%SCRIPT_DIR%launcher_server.py" >> launcher_log.txt 2>&1

echo [%date% %time%] launcher_server.py stopped (exit code %errorlevel%). Restarting in 3 seconds... >> launcher_log.txt
echo [%date% %time%] Note: this only fires if the SERVER process exits (crash, killed, etc). >> launcher_log.txt
echo [%date% %time%] Closing just the Chrome kiosk window does NOT stop the server or trigger a restart. >> launcher_log.txt
timeout /t 3 /nobreak >nul
goto loop