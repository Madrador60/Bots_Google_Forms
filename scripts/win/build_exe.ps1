$ErrorActionPreference = "Stop"

$rootDir = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$appDir = Join-Path $rootDir "app"
$entryPoint = Join-Path $appDir "Interface_GoogleForm_Studio.py"
$distDir = Join-Path $rootDir "dist"
$buildDir = Join-Path $rootDir "build"

function Write-Step($message) {
    Write-Host "[Google Form Studio] $message"
}

function Invoke-Python {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)

    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        & py -3 @Args | ForEach-Object { Write-Host $_ }
        return [int]$LASTEXITCODE
    }

    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        & python @Args | ForEach-Object { Write-Host $_ }
        return [int]$LASTEXITCODE
    }

    throw "Python est introuvable. Installe Python 3 puis relance le build."
}

Write-Step "Installation des dependances de build..."
$exitCode = Invoke-Python -m pip install -r (Join-Path $rootDir "requirements.txt") pyinstaller
if ($exitCode -ne 0) {
    throw "Installation des dependances echouee."
}

Write-Step "Nettoyage des anciens builds..."
if (Test-Path -LiteralPath $distDir) {
    Remove-Item -LiteralPath $distDir -Recurse -Force
}
if (Test-Path -LiteralPath $buildDir) {
    Remove-Item -LiteralPath $buildDir -Recurse -Force
}

Write-Step "Creation de l'executable Windows..."
$exitCode = Invoke-Python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --name "GoogleFormStudio" `
    --paths $appDir `
    --distpath $distDir `
    --workpath $buildDir `
    $entryPoint

if ($exitCode -ne 0) {
    throw "Build PyInstaller echoue."
}

$exePath = Join-Path $distDir "GoogleFormStudio.exe"
if (-not (Test-Path -LiteralPath $exePath)) {
    throw "Executable introuvable apres le build."
}

Write-Host ""
Write-Step "Executable cree avec succes:"
Write-Host $exePath
