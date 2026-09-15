@echo off
echo Stopping the launcher server, its watchdog, and the kiosk window...

rem Kill the watchdog (the cmd.exe running start_launcher.bat's loop) by
rem matching its command line, so this doesn't close unrelated cmd windows.
powershell -NoProfile -Command ^
    "Get-CimInstance Win32_Process -Filter \"Name='cmd.exe'\" | Where-Object { $_.CommandLine -like '*start_launcher.bat*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"

rem Kill launcher_server.py itself. Matched on any process whose
rem name starts with "python" (covers python.exe, pythonw.exe, and
rem versioned builds like the Microsoft Store's "pythonw3.13.exe")
rem AND whose command line contains launcher_server.py - so this
rem won't touch an unrelated Python process, or an editor/IDE that
rem merely has this file open.
powershell -NoProfile -Command ^
    "Get-CimInstance Win32_Process -Filter \"Name LIKE 'python%'\" | Where-Object { $_.CommandLine -like '*launcher_server.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"

rem Kill ONLY the kiosk Chrome window (matched by --kiosk in its command
rem line) - not your regular Chrome windows/tabs on this PC.
powershell -NoProfile -Command ^
    "Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" | Where-Object { $_.CommandLine -like '*--kiosk*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"

echo Done - watchdog, server, and kiosk window are stopped. Your regular
echo Chrome windows/tabs were left alone.
pause