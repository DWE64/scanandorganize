# BASIC Scanner - Installation automatique (Windows)
# Exécution : .\install.ps1  ou  powershell -ExecutionPolicy Bypass -File install.ps1
# Options : -SkipVenv  (ne pas créer/activer le venv), -SkipTests  (ne pas lancer les tests)

param(
    [switch]$SkipVenv,
    [switch]$SkipTests,
    [switch]$NoDev  # installer sans dépendances de dev (pytest, etc.)
)

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot

Write-Host "=== BASIC Scanner - Installation automatique ===" -ForegroundColor Cyan
Write-Host ""

# --- Vérifier Python 3.11+ ---
$pythonCmd = $null
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $v = & $cmd --version 2>&1
        if ($v -match "Python 3\.(1[1-9]|[2-9][0-9])") {
            $pythonCmd = $cmd
            break
        }
    } catch {}
}
if (-not $pythonCmd) {
    Write-Host "ERREUR : Python 3.11 ou supérieur est requis." -ForegroundColor Red
    Write-Host "Téléchargez-le sur https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}
Write-Host "[OK] Python trouvé : $pythonCmd" -ForegroundColor Green

# --- Environnement virtuel ---
$venvPath = Join-Path $ProjectRoot ".venv"
$venvActivate = Join-Path $venvPath "Scripts\Activate.ps1"

if (-not $SkipVenv) {
    if (-not (Test-Path $venvPath)) {
        Write-Host "Création de l'environnement virtuel (.venv)..." -ForegroundColor Yellow
        & $pythonCmd -m venv $venvPath
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        Write-Host "[OK] Environnement virtuel créé." -ForegroundColor Green
    } else {
        Write-Host "[OK] Environnement virtuel existant (.venv)." -ForegroundColor Green
    }
    if (Test-Path $venvActivate) {
        . $venvActivate
        $pipCmd = "pip"
        $pythonExe = "python"
    } else {
        $pipCmd = "$pythonCmd -m pip"
        $pythonExe = $pythonCmd
    }
} else {
    $pipCmd = "$pythonCmd -m pip"
    $pythonExe = $pythonCmd
}

# --- Installation des dépendances ---
Push-Location $ProjectRoot
try {
    Write-Host "Installation des dépendances Python..." -ForegroundColor Yellow
    if ($NoDev) {
        & $pythonExe -m pip install -e . -q
    } else {
        & $pythonExe -m pip install -e ".[dev]" -q
    }
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Write-Host "[OK] Dépendances installées." -ForegroundColor Green
} finally {
    Pop-Location
}

# --- Fichier de configuration ---
$configYaml = Join-Path $ProjectRoot "config.yaml"
$configExample = Join-Path $ProjectRoot "config.example.yaml"
if (-not (Test-Path $configYaml) -and (Test-Path $configExample)) {
    Copy-Item $configExample $configYaml
    Write-Host "[OK] config.yaml créé à partir de config.example.yaml." -ForegroundColor Green
    Write-Host "     Pensez à éditer config.yaml (inbox, racine_destination, etc.)." -ForegroundColor Yellow
} elseif (Test-Path $configYaml) {
    Write-Host "[OK] config.yaml déjà présent." -ForegroundColor Green
}

# --- Vérification Tesseract ---
$tesseractOk = $false
try {
    $tess = Get-Command tesseract -ErrorAction SilentlyContinue
    if ($tess) {
        & tesseract --version 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) { $tesseractOk = $true }
    }
} catch {}
if ($tesseractOk) {
    Write-Host "[OK] Tesseract OCR trouvé." -ForegroundColor Green
} else {
    Write-Host "[!] Tesseract OCR non trouvé ou pas dans le PATH." -ForegroundColor Yellow
    Write-Host "    Pour l'OCR des PDF scannés, installez Tesseract :" -ForegroundColor Yellow
    if (Get-Command choco -ErrorAction SilentlyContinue) {
        Write-Host "    choco install tesseract" -ForegroundColor Gray
    } else {
        Write-Host "    https://github.com/UB-Mannheim/tesseract/wiki" -ForegroundColor Gray
    }
}

# --- Vérification Ghostscript ---
$gsOk = $false
foreach ($gs in @("gswin64c", "gswin32c")) {
    try {
        $c = Get-Command $gs -ErrorAction SilentlyContinue
        if ($c) { $gsOk = $true; break }
    } catch {}
}
if ($gsOk) {
    Write-Host "[OK] Ghostscript trouvé." -ForegroundColor Green
} else {
    Write-Host "[!] Ghostscript non trouvé (requis par ocrmypdf pour l'OCR)." -ForegroundColor Yellow
    Write-Host "    https://ghostscript.com/releases/gsdnld.html" -ForegroundColor Gray
}

# --- Tests optionnels ---
if (-not $SkipTests -and -not $NoDev) {
    Write-Host ""
    Write-Host "Lancement des tests..." -ForegroundColor Yellow
    & $pythonExe -m pytest tests/ -v --tb=short -q 2>&1 | Out-Host
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] Tous les tests sont passés." -ForegroundColor Green
    } else {
        Write-Host "[!] Certains tests ont échoué (code $LASTEXITCODE)." -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "=== Installation terminée ===" -ForegroundColor Cyan
if (-not $SkipVenv) {
    Write-Host "Pour lancer l'application, activez le venv puis :" -ForegroundColor White
    Write-Host "  .\.venv\Scripts\Activate.ps1" -ForegroundColor Gray
}
Write-Host "  basic_scanner run --config config.yaml" -ForegroundColor Gray
Write-Host "  basic_scanner test-file chemin/vers/fichier.pdf --config config.yaml" -ForegroundColor Gray
Write-Host ""
