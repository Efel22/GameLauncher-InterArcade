@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo Diagnostic run: %date% %time% > launcher_diag.txt
echo. >> launcher_diag.txt

echo === Is anything listening on port 8765? === >> launcher_diag.txt
netstat -ano -p tcp | findstr :8765 >> launcher_diag.txt
echo. >> launcher_diag.txt

echo === Test: does "Name LIKE python%%" match anything at all? === >> launcher_diag.txt
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name LIKE 'python%%'\" | Select-Object ProcessId, Name | Format-List" >> launcher_diag.txt
echo (empty above this line means the LIKE filter matched zero processes) >> launcher_diag.txt
echo. >> launcher_diag.txt

echo === Test: same query, but unfiltered by name, then filtered on CommandLine in PowerShell === >> launcher_diag.txt
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*launcher_server.py*' } | Select-Object ProcessId, Name, CommandLine | Format-List" >> launcher_diag.txt
echo. >> launcher_diag.txt

echo === Test: full combined query exactly as start_launcher.bat runs it (dry run - lists only, does not kill) === >> launcher_diag.txt
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name LIKE 'python%%'\" | Where-Object { $_.CommandLine -like '*launcher_server.py*' } | Select-Object ProcessId, Name, CommandLine | Format-List" >> launcher_diag.txt
echo (empty above this line means the combined filter matched zero processes) >> launcher_diag.txt

echo. >> launcher_diag.txt
echo Diagnostic saved to launcher_diag.txt >> launcher_diag.txt

echo Done - results saved to launcher_diag.txt. You can close this window.
pause
