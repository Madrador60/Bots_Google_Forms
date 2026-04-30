@echo off
setlocal

cd /d "%~dp0"

echo Desinstallation de Google Form Studio...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0uninstall.ps1"
echo.
pause
