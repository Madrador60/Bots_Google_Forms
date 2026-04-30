@echo off
setlocal

cd /d "%~dp0"

set "LOG_DIR=%~dp0logs"
set "LOG_FILE=%LOG_DIR%\google_form_studio.log"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

echo Lancement de Google Form Studio...
echo Journal: "%LOG_FILE%"
call "%~dp0_Executer_Python_Windows.bat" "Interface_GoogleForm_Studio.py" > "%LOG_FILE%" 2>&1

if %errorlevel%==0 exit /b 0

echo.
echo L'interface graphique n'a pas pu demarrer.
echo Regarde le journal ici:
echo "%LOG_FILE%"
echo.
echo Ouverture du mode terminal en secours...
echo ----------------------------------------------------------
call "%~dp0_Executer_Python_Windows.bat" "Bot_GoogleForm_Intelligent.py"
pause
