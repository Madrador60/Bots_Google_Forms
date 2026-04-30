$ErrorActionPreference = "Stop"

$installerUrl = "https://raw.githubusercontent.com/Madrador60/Bots_Google_Forms/main/install.ps1"
$tempInstaller = Join-Path $env:TEMP ("googleform_update_" + [Guid]::NewGuid().ToString("N") + ".ps1")

function Write-Step($message) {
    Write-Host "[Google Form Studio] $message"
}

try {
    Write-Step "Telechargement de la derniere version..."
    Invoke-WebRequest -UseBasicParsing -Uri $installerUrl -OutFile $tempInstaller

    Write-Step "Mise a jour..."
    & powershell -NoProfile -ExecutionPolicy Bypass -File $tempInstaller -NoLaunch

    Write-Host ""
    Write-Step "Mise a jour terminee."
    Write-Host "Tu peux lancer l'application avec : googleform"
} finally {
    if (Test-Path -LiteralPath $tempInstaller) {
        Remove-Item -LiteralPath $tempInstaller -Force
    }
}
