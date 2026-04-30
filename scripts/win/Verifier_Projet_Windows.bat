@echo off
setlocal

cd /d "%~dp0"

set "ROOT_DIR=%~dp0..\.."
for %%I in ("%ROOT_DIR%") do set "ROOT_DIR=%%~fI"
set "APP_DIR=%ROOT_DIR%\app"

set "PYTHONDONTWRITEBYTECODE=1"

echo Verification de la compilation...
call "%~dp0Executer_Python_Windows.bat" -m py_compile "%APP_DIR%\Bot_GoogleForm_Intelligent.py" "%APP_DIR%\Interface_GoogleForm_Studio.py"
if errorlevel 1 goto failed

echo Execution des tests...
set "PYTHONPATH=%APP_DIR%;%PYTHONPATH%"
call "%~dp0Executer_Python_Windows.bat" -m unittest discover -s "%ROOT_DIR%\tests" -p "test_*.py"
if errorlevel 1 goto failed

echo.
echo Verification terminee avec succes.
pause
exit /b 0

:failed
echo.
echo Verification echouee.
pause
exit /b 1
