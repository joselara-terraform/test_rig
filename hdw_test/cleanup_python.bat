@echo off
echo Waiting for emergency script to finish...
timeout /t 2 /nobreak >nul
echo Killing Python processes...
taskkill /F /IM python.exe >nul 2>&1
taskkill /F /IM pythonw.exe >nul 2>&1
echo Cleanup complete
del "%~f0"
