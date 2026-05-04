param(
    [switch]$NoLaunch
)

$ErrorActionPreference = "Stop"

$appVersion = "1.0.0"
$exeUrl = "https://github.com/Madrador60/Bots_Google_Forms/releases/latest/download/GoogleFormStudio.exe"
$installDir = Join-Path $env:LOCALAPPDATA "GoogleFormStudio"
$exePath = Join-Path $installDir "GoogleFormStudio.exe"
$launcherPath = Join-Path $installDir "googleform.bat"

function Write-Step($message) {
    Write-Host "[Google Form Studio] $message"
}

Write-Step "Installation de la version EXE dans $installDir"

New-Item -ItemType Directory -Path $installDir -Force | Out-Null

Write-Step "Telechargement de GoogleFormStudio.exe..."
Invoke-WebRequest -UseBasicParsing -Uri $exeUrl -OutFile $exePath

$launcherContent = @'
@echo off
setlocal

set "APP_VERSION=__APP_VERSION__"

if /i "%~1"=="uninstall" goto uninstall
if /i "%~1"=="desinstaller" goto uninstall
if /i "%~1"=="--uninstall" goto uninstall
if /i "%~1"=="update" goto update
if /i "%~1"=="maj" goto update
if /i "%~1"=="--update" goto update
if /i "%~1"=="version" goto version
if /i "%~1"=="--version" goto version
if /i "%~1"=="-v" goto version

start "" "%~dp0GoogleFormStudio.exe"
exit /b 0

:update
powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/Madrador60/Bots_Google_Forms/main/installer.ps1 | iex"
exit /b %errorlevel%

:version
echo Google Form Studio v%APP_VERSION%
exit /b 0

:uninstall
powershell -NoProfile -ExecutionPolicy Bypass -Command "$dir = '%~dp0'.TrimEnd('\'); $path = [Environment]::GetEnvironmentVariable('Path','User'); if ($path) { $new = (($path -split ';') | Where-Object { $_ -and ($_.TrimEnd('\') -ne $dir) }) -join ';'; [Environment]::SetEnvironmentVariable('Path', $new, 'User') }; Start-Process cmd.exe -ArgumentList '/c timeout /t 2 /nobreak >nul & rmdir /s /q ""%~dp0""' -WindowStyle Hidden"
echo Google Form Studio sera supprime dans quelques secondes.
exit /b 0
'@

$launcherContent = $launcherContent.Replace("__APP_VERSION__", $appVersion)

Set-Content -LiteralPath $launcherPath -Value $launcherContent -Encoding ASCII

$currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
$pathParts = @()
if (-not [string]::IsNullOrWhiteSpace($currentPath)) {
    $pathParts = $currentPath -split ";"
}

if ($pathParts -notcontains $installDir) {
    Write-Step "Ajout de googleform au PATH utilisateur..."
    $newPath = if ([string]::IsNullOrWhiteSpace($currentPath)) {
        $installDir
    } else {
        $currentPath.TrimEnd(";") + ";" + $installDir
    }
    [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
    $env:Path = $env:Path.TrimEnd(";") + ";" + $installDir
}

Write-Host ""
Write-Step "Installation terminee."
Write-Host "Version : v$appVersion"
Write-Host "Dossier installe : $installDir"
Write-Host "Commande : googleform"

if (-not $NoLaunch) {
    Write-Step "Lancement de Google Form Studio..."
    Start-Process -FilePath $exePath -WorkingDirectory $installDir
}

Write-Host "Si googleform n'est pas reconnu plus tard, ferme puis rouvre le CMD/PowerShell."
