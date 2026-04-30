@echo off
setlocal

cd /d "%~dp0"

set "LOG_DIR=%~dp0logs"
set "LOG_FILE=%LOG_DIR%\google_form_studio.log"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

where py >nul 2>nul
if %errorlevel%==0 (
    set "PYTHON_CMD=py -3"
    goto run_app
)

where python >nul 2>nul
if %errorlevel%==0 (
    set "PYTHON_CMD=python"
    goto run_app
)

echo Python n'est pas installe ou n'est pas disponible dans le PATH.
echo Installe Python depuis https://www.python.org/downloads/windows/
echo Coche bien "Add Python to PATH" pendant l'installation.
pause
exit /b 1

:run_app
echo Lancement de Google Form Studio...
echo Journal: "%LOG_FILE%"
%PYTHON_CMD% "Interface_GoogleForm_Studio.py" > "%LOG_FILE%" 2>&1

if %errorlevel%==0 exit /b 0

echo.
echo L'interface graphique n'a pas pu demarrer.
echo Regarde le journal ici:
echo "%LOG_FILE%"
echo.
echo Ouverture du mode terminal en secours...
echo ----------------------------------------------------------
%PYTHON_CMD% "Bot_GoogleForm_Intelligent.py"
pause
