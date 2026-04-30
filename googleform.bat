@echo off
setlocal

cd /d "%~dp0"

set "ROOT_DIR=%~dp0"
set "SCRIPTS_DIR=%ROOT_DIR%scripts\windows"
set "APP_DIR=%ROOT_DIR%app"

if /i "%~1"=="--cli" goto run_cli
if /i "%~1"=="cli" goto run_cli
if /i "%~1"=="--test" goto run_tests
if /i "%~1"=="test" goto run_tests
if /i "%~1"=="--install" goto install_deps
if /i "%~1"=="install" goto install_deps
if /i "%~1"=="--update" goto update_app
if /i "%~1"=="update" goto update_app
if /i "%~1"=="maj" goto update_app
if /i "%~1"=="--uninstall" goto uninstall_app
if /i "%~1"=="uninstall" goto uninstall_app
if /i "%~1"=="desinstaller" goto uninstall_app
if /i "%~1"=="--help" goto help
if /i "%~1"=="help" goto help
if /i "%~1"=="/?" goto help

call "%SCRIPTS_DIR%\Lancer_GoogleForm_Studio.bat"
exit /b %errorlevel%

:run_cli
call "%SCRIPTS_DIR%\Executer_Python_Windows.bat" "%APP_DIR%\Bot_GoogleForm_Intelligent.py"
exit /b %errorlevel%

:run_tests
call "%SCRIPTS_DIR%\Verifier_Projet_Windows.bat"
exit /b %errorlevel%

:install_deps
call "%SCRIPTS_DIR%\Installer_Dependances_Windows.bat"
exit /b %errorlevel%

:update_app
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPTS_DIR%\update.ps1"
exit /b %errorlevel%

:uninstall_app
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPTS_DIR%\uninstall.ps1"
exit /b %errorlevel%

:help
echo Google Form Studio
echo.
echo Commandes:
echo   googleform          Lance l'interface graphique
echo   googleform cli      Lance le mode terminal
echo   googleform install  Installe les dependances Python
echo   googleform update   Met a jour Google Form Studio
echo   googleform uninstall  Desinstalle Google Form Studio
echo   googleform test     Lance les tests
echo   googleform help     Affiche cette aide
echo.
exit /b 0
