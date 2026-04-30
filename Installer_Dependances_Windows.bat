@echo off
setlocal

cd /d "%~dp0"

echo Installation des dependances Python...
call "%~dp0_Executer_Python_Windows.bat" -m pip install -r requirements.txt
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
