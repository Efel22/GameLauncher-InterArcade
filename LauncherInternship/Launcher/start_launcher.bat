@echo off
setlocal

rem Folder this script lives in - resolved automatically so this works no
rem matter where it's placed on the arcade PC, no path to edit.
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

rem ------------------------------------------------------------------
rem Clean up any previous launcher instance before starting fresh.
rem
rem This makes it safe to (re)run this file at any time - after a
rem crash, after the arcade PC didn't shut down cleanly, or just to
rem force the Chrome kiosk window back open - without hitting
rem "file in use" errors or ending up with two kiosk windows.
rem Matched by command line, so this won't touch unrelated Python
rem or Chrome processes. Runs before we ever touch launcher_log.txt,
rem since a leftover process holding it open is exactly what we're
rem clearing here.
rem ------------------------------------------------------------------

powershell -NoProfile -Command ^
    "Get-CimInstance Win32_Process -Filter \"Name LIKE 'python%%'\" | Where-Object { $_.CommandLine -like '*launcher_server.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
powershell -NoProfile -Command ^
    "Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" | Where-Object { $_.CommandLine -like '*--kiosk*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"

rem Give Windows a moment to fully release the log file handle.

timeout /t 1 /nobreak >nul

rem ------------------------------------------------------------------
rem Rotate the log if it's gotten large, so it doesn't grow forever.
rem
rem If launcher_log.txt is over 5 MB, move it to launcher_log.old.txt
rem (overwriting any previous rotation) and start fresh. Keeps
rem "current + one previous rotation" of history without letting
rem the file grow without bound over months of daily use.
rem ------------------------------------------------------------------

for %%A in ("launcher_log.txt") do if %%~zA GTR 5242880 move /y "launcher_log.txt" "launcher_log.old.txt" >nul

:loop
echo [%date% %time%] Starting launcher_server.py... >> launcher_log.txt

rem pythonw runs without popping its own console window. If "pythonw" isn't
rem recognized, change this to "python" (you'll get a small console box too,
rem but it'll still work). launcher_server.py serves launcher.html, opens
rem Chrome in kiosk mode, and handles /launch requests to start games.
rem
rem -u forces unbuffered stdout/stderr. Without it, Python block-buffers
rem output once it's redirected to a file, so none of the print()
rem messages (game launches, window search results) would actually
rem show up in launcher_log.txt until the process exits cleanly - and
rem since we force-kill it on every restart, that output was silently
rem lost. -u makes it write to the log immediately, in real time.
pythonw -u "%SCRIPT_DIR%launcher_server.py" >> launcher_log.txt 2>&1

echo [%date% %time%] launcher_server.py stopped (exit code %errorlevel%). Restarting in 3 seconds... >> launcher_log.txt
echo [%date% %time%] Note: this only fires if the SERVER process exits (crash, killed, etc). >> launcher_log.txt
echo [%date% %time%] Closing just the Chrome kiosk window does NOT stop the server or trigger a restart. >> launcher_log.txt
timeout /t 3 /nobreak >nul
goto loop