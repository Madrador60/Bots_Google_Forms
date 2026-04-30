@echo off
setlocal

cd /d "%~dp0"

set "ROOT_DIR=%~dp0..\.."
for %%I in ("%ROOT_DIR%") do set "ROOT_DIR=%%~fI"
set "APP_DIR=%ROOT_DIR%\app"
set "LOG_DIR=%ROOT_DIR%\logs"
set "LOG_FILE=%LOG_DIR%\google_form_studio.log"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

echo Lancement de Google Form Studio...
echo Journal: "%LOG_FILE%"
call "%~dp0Executer_Python_Windows.bat" "%APP_DIR%\Interface_GoogleForm_Studio.py" > "%LOG_FILE%" 2>&1

if %errorlevel%==0 exit /b 0

echo.
echo L'interface graphique n'a pas pu demarrer.
echo Regarde le journal ici:
echo "%LOG_FILE%"
echo.
echo Ouverture du mode terminal en secours...
echo ----------------------------------------------------------
call "%~dp0Executer_Python_Windows.bat" "%APP_DIR%\Bot_GoogleForm_Intelligent.py"
pause
