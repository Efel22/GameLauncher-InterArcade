@echo off
setlocal

rem Folder this script lives in - resolved automatically so this works no
rem matter where it's placed on the arcade PC, no path to edit.
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

:loop
echo [%date% %time%] Starting launcher... >> launcher_log.txt

rem pythonw runs without popping its own console window. If "pythonw" isn't
rem recognized, change this to "python" (you'll get a small console box too,
rem but it'll still work).
pythonw "%SCRIPT_DIR%LauncherTest_E.py" >> launcher_log.txt 2>&1

echo [%date% %time%] Launcher closed (exit code %errorlevel%). Restarting in 3 seconds... >> launcher_log.txt
timeout /t 3 /nobreak >nul
goto loop