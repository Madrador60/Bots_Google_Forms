@echo off
setlocal EnableExtensions

set "APP_DIR=%~dp0..\.."
for %%I in ("%APP_DIR%") do set "APP_DIR=%%~fI"

echo Installation de la commande googleform pour le CMD...
echo Dossier: "%APP_DIR%"
echo.

where setx >nul 2>nul
if errorlevel 1 (
    echo La commande setx est introuvable sur ce Windows.
    echo Ajoute manuellement ce dossier au PATH utilisateur:
    echo "%APP_DIR%"
    pause
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "$dir = '%APP_DIR%'; $current = [Environment]::GetEnvironmentVariable('Path', 'User'); if ([string]::IsNullOrWhiteSpace($current)) { $new = $dir } elseif (($current -split ';') -contains $dir) { $new = $current } else { $new = $current.TrimEnd(';') + ';' + $dir }; [Environment]::SetEnvironmentVariable('Path', $new, 'User')"
if errorlevel 1 goto failed

echo.
echo Commande installee.
echo Ferme puis rouvre le CMD, puis tape:
echo   googleform
echo.
echo Autres commandes utiles:
echo   googleform cli
echo   googleform install
echo   googleform uninstall
echo   googleform test
pause
exit /b 0

:failed
echo.
echo Installation de la commande echouee.
pause
exit /b 1
