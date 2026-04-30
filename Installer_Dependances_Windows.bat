@echo off
setlocal

cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    set "PYTHON_CMD=py -3"
    goto install
)

where python >nul 2>nul
if %errorlevel%==0 (
    set "PYTHON_CMD=python"
    goto install
)

echo Python n'est pas installe ou n'est pas disponible dans le PATH.
echo Installe Python depuis https://www.python.org/downloads/windows/
echo Coche bien "Add Python to PATH" pendant l'installation.
pause
exit /b 1

:install
echo Installation des dependances Python...
%PYTHON_CMD% -m pip install -r requirements.txt
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
