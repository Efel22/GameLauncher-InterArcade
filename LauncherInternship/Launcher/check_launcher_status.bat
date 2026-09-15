@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo Diagnostic run: %date% %time% > launcher_diag.txt
echo. >> launcher_diag.txt

echo === Who am I running as? === >> launcher_diag.txt
whoami >> launcher_diag.txt
echo. >> launcher_diag.txt

echo === Whatever is on port 8765 right now (PID + full details) === >> launcher_diag.txt
for /f "tokens=5" %%P in ('netstat -ano -p tcp ^| findstr :8765 ^| findstr LISTENING') do (
    echo Port 8765 PID: %%P >> launcher_diag.txt
    powershell -NoProfile -Command "Get-Process -Id %%P -ErrorAction SilentlyContinue | Select-Object Id, ProcessName, Path, StartTime | Format-List" >> launcher_diag.txt
    powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"ProcessId=%%P\" | Select-Object ProcessId, Name, CommandLine, ExecutablePath | Format-List" >> launcher_diag.txt
)

echo === ALL pythonw.exe / python.exe processes, unfiltered === >> launcher_diag.txt
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='pythonw.exe' OR Name='python.exe'\" | Select-Object ProcessId, Name, CommandLine | Format-List" >> launcher_diag.txt

echo === ALL cmd.exe processes, unfiltered === >> launcher_diag.txt
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='cmd.exe'\" | Select-Object ProcessId, CommandLine | Format-List" >> launcher_diag.txt

echo. >> launcher_diag.txt
echo Diagnostic saved to launcher_diag.txt >> launcher_diag.txt

echo Done - results saved to launcher_diag.txt. You can close this window.
pause
