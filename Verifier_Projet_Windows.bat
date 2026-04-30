@echo off
setlocal

cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    set "PYTHON_CMD=py -3"
    goto verify
)

where python >nul 2>nul
if %errorlevel%==0 (
    set "PYTHON_CMD=python"
    goto verify
)

echo Python n'est pas installe ou n'est pas disponible dans le PATH.
echo Installe Python depuis https://www.python.org/downloads/windows/
echo Coche bien "Add Python to PATH" pendant l'installation.
pause
exit /b 1

:verify
set "PYTHONDONTWRITEBYTECODE=1"

echo Verification de la compilation...
%PYTHON_CMD% -m py_compile "Bot_GoogleForm_Intelligent.py" "Interface_GoogleForm_Studio.py"
if errorlevel 1 goto failed

echo Execution des tests...
%PYTHON_CMD% -m unittest discover -s tests -p "test_*.py"
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
