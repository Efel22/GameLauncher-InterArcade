@echo off
echo Stopping the launcher and its watchdog loop...

rem Kill the watchdog (the cmd.exe running start_launcher.bat's loop) by
rem matching its command line, so this doesn't close unrelated cmd windows.
powershell -NoProfile -Command ^
    "Get-CimInstance Win32_Process -Filter \"Name='cmd.exe'\" | Where-Object { $_.CommandLine -like '*start_launcher.bat*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"

rem Kill the app itself, however it was launched (pythonw or python).
taskkill /F /IM pythonw.exe >nul 2>&1
taskkill /F /IM python.exe  >nul 2>&1

echo Done - the launcher and its watchdog are stopped. It will NOT come back
echo on its own until you run start_launcher.bat / run_launcher_hidden.vbs
echo again, or the PC restarts (if the Startup shortcut is still in place).
pause