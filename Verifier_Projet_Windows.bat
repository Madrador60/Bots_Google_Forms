@echo off
setlocal

cd /d "%~dp0"

set "PYTHONDONTWRITEBYTECODE=1"

echo Verification de la compilation...
call "%~dp0_Executer_Python_Windows.bat" -m py_compile "Bot_GoogleForm_Intelligent.py" "Interface_GoogleForm_Studio.py"
if errorlevel 1 goto failed

echo Execution des tests...
call "%~dp0_Executer_Python_Windows.bat" -m unittest discover -s tests -p "test_*.py"
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
