@echo off
setlocal

cd /d "%~dp0"

set "ROOT_DIR=%~dp0..\.."
for %%I in ("%ROOT_DIR%") do set "ROOT_DIR=%%~fI"

echo Installation des dependances Python...
call "%~dp0Executer_Python_Windows.bat" -m pip install -r "%ROOT_DIR%\requirements.txt"
if errorlevel 1 goto failed

echo.
echo Dependances installees avec succes.
pause
exit /b 0

:failed
echo.
echo Installation echouee.
pause
exit /b 1
