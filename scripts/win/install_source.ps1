param(
    [switch]$NoLaunch
)

$ErrorActionPreference = "Stop"

$repoZipUrl = "https://github.com/Madrador60/Bots_Google_Forms/archive/refs/heads/main.zip"
$installDir = Join-Path $env:LOCALAPPDATA "Bots_Google_Forms"
$tempRoot = Join-Path $env:TEMP ("Bots_Google_Forms_" + [Guid]::NewGuid().ToString("N"))
$zipPath = Join-Path $tempRoot "source.zip"

function Write-Step($message) {
    Write-Host "[Google Form Studio] $message"
}

function Test-Python {
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        return @{ Command = "py"; Args = @("-3") }
    }

    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        return @{ Command = "python"; Args = @() }
    }

    return $null
}

Write-Step "Installation dans $installDir"

New-Item -ItemType Directory -Path $tempRoot -Force | Out-Null
New-Item -ItemType Directory -Path $installDir -Force | Out-Null

try {
    Write-Step "Telechargement du projet depuis GitHub..."
    Invoke-WebRequest -UseBasicParsing -Uri $repoZipUrl -OutFile $zipPath

    Write-Step "Extraction..."
    Expand-Archive -LiteralPath $zipPath -DestinationPath $tempRoot -Force
    $sourceDir = Get-ChildItem -LiteralPath $tempRoot -Directory |
        Where-Object { $_.Name -like "Bots_Google_Forms-*" } |
        Select-Object -First 1

    if (-not $sourceDir) {
        throw "Archive GitHub invalide: dossier source introuvable."
    }

    $obsoleteFiles = @(
        "Bot_GoogleForm_Intelligent.py",
        "Interface_GoogleForm_Studio.py",
        "Desinstaller_GoogleForm_Studio.bat",
        "Installer_Commande_CMD_Windows.bat",
        "Installer_Dependances_Windows.bat",
        "Lancer_GoogleForm_Studio.bat",
        "Verifier_Projet_Windows.bat",
        "_Executer_Python_Windows.bat",
        "uninstall.ps1",
        "LISEZ_MOI.txt"
    )

    foreach ($fileName in $obsoleteFiles) {
        $path = Join-Path $installDir $fileName
        if (Test-Path -LiteralPath $path) {
            Remove-Item -LiteralPath $path -Force
        }
    }

    Write-Step "Copie des fichiers..."
    Copy-Item -Path (Join-Path $sourceDir.FullName "*") -Destination $installDir -Recurse -Force

    $currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $pathParts = @()
    if (-not [string]::IsNullOrWhiteSpace($currentPath)) {
        $pathParts = $currentPath -split ";"
    }

    if ($pathParts -notcontains $installDir) {
        Write-Step "Ajout de la commande googleform au PATH utilisateur..."
        $newPath = if ([string]::IsNullOrWhiteSpace($currentPath)) {
            $installDir
        } else {
            $currentPath.TrimEnd(";") + ";" + $installDir
        }
        [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
        $env:Path = $env:Path.TrimEnd(";") + ";" + $installDir
    }

    $python = Test-Python
    if ($python) {
        Write-Step "Installation des dependances Python..."
        & $python.Command @($python.Args + @("-m", "pip", "install", "-r", (Join-Path $installDir "requirements.txt")))
    } else {
        Write-Host ""
        Write-Warning "Python n'a pas ete trouve. Installe Python 3 puis relance cette commande."
        Write-Host "https://www.python.org/downloads/windows/"
        exit 1
    }

    Write-Host ""
    Write-Step "Installation terminee."
    if (-not $NoLaunch) {
        Write-Host "Lancement de Google Form Studio..."
        Write-Host ""
        Start-Process -FilePath (Join-Path $installDir "googleform.bat") -WorkingDirectory $installDir
    }
    Write-Host "Si la commande googleform n'est pas reconnue plus tard, ferme puis rouvre le CMD/PowerShell."
} finally {
    if (Test-Path -LiteralPath $tempRoot) {
        Remove-Item -LiteralPath $tempRoot -Recurse -Force
    }
}
