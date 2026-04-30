$ErrorActionPreference = "Stop"

$installDir = Join-Path $env:LOCALAPPDATA "Bots_Google_Forms"

function Write-Step($message) {
    Write-Host "[Google Form Studio] $message"
}

Write-Step "Desinstallation..."

$currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
if (-not [string]::IsNullOrWhiteSpace($currentPath)) {
    $pathParts = $currentPath -split ";" |
        Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
        Where-Object { $_.TrimEnd("\") -ne $installDir.TrimEnd("\") }

    $newPath = $pathParts -join ";"
    [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
    Write-Step "Commande googleform retiree du PATH utilisateur."
}

if (Test-Path -LiteralPath $installDir) {
    $cleanupScript = Join-Path $env:TEMP ("googleform_uninstall_" + [Guid]::NewGuid().ToString("N") + ".cmd")
    $cleanupContent = @"
@echo off
timeout /t 2 /nobreak >nul
rmdir /s /q "$installDir" 2>nul
del "%~f0" >nul 2>nul
"@
    Set-Content -LiteralPath $cleanupScript -Value $cleanupContent -Encoding ASCII
    Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "`"$cleanupScript`"" -WorkingDirectory $env:TEMP -WindowStyle Hidden
    Write-Step "Suppression du dossier programme planifiee."
}

Write-Host ""
Write-Step "Desinstallation terminee."
Write-Host "Ferme puis rouvre le CMD ou PowerShell pour actualiser le PATH."
