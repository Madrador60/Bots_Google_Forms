@echo off
setlocal

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 %*
    exit /b %errorlevel%
)

where python >nul 2>nul
if %errorlevel%==0 (
    python %*
    exit /b %errorlevel%
)

echo Python n'est pas installe ou n'est pas disponible dans le PATH.
echo Installe Python depuis https://www.python.org/downloads/windows/
echo Coche bien "Add Python to PATH" pendant l'installation.
exit /b 1
