# BASIC Scanner - Vérification de l'installation
# Exécution : .\verify.ps1  ou  powershell -ExecutionPolicy Bypass -File verify.ps1
# Code de sortie : 0 = OK, 1 = au moins un contrôle en échec

param(
    [switch]$Quick   # ne lance pas les tests pytest (vérification minimale)
)

$ErrorActionPreference = "Continue"
$ProjectRoot = $PSScriptRoot
$failed = 0

function Test-Step {
    param([string]$Name, [scriptblock]$Check, [string]$FailMessage = "Échec")
    Write-Host -NoNewline "  $Name ... "
    try {
        $result = & $Check
        if ($result) {
            Write-Host "[OK]" -ForegroundColor Green
            return $true
        }
    } catch {}
    Write-Host "[ÉCHEC]" -ForegroundColor Red
    if ($FailMessage) { Write-Host "    $FailMessage" -ForegroundColor Gray }
    return $false
}

Write-Host ""
Write-Host "=== BASIC Scanner - Vérification de l'installation ===" -ForegroundColor Cyan
Write-Host ""

# --- Python utilisé (venv prioritaire) ---
$venvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$pythonExe = $null
if (Test-Path $venvPython) {
    $pythonExe = $venvPython
    Write-Host "Environnement : .venv (projet)" -ForegroundColor Gray
} else {
    foreach ($cmd in @("python", "python3", "py")) {
        try {
            $v = & $cmd --version 2>&1
            if ($v -match "Python 3\.(1[1-9]|[2-9][0-9])") {
                $pythonExe = $cmd
                break
            }
        } catch {}
    }
    if ($pythonExe) { Write-Host "Environnement : Python système ($pythonExe)" -ForegroundColor Gray }
}
Write-Host ""

if (-not $pythonExe) {
    Write-Host "[ÉCHEC] Python 3.11+ introuvable. Exécutez install.ps1 d'abord." -ForegroundColor Red
    exit 1
}

# --- 1. Version Python ---
Write-Host "1. Python 3.11+" -ForegroundColor White
$v = & $pythonExe --version 2>&1
if ($v -match "Python 3\.(1[1-9]|[2-9][0-9])") {
    Write-Host "  $v [OK]" -ForegroundColor Green
} else {
    Write-Host "  $v [ÉCHEC]" -ForegroundColor Red
    $failed++
}
Write-Host ""

# --- 2. Package basic_scanner importable ---
Write-Host "2. Package basic_scanner" -ForegroundColor White
$importOk = $false
try {
    Push-Location $ProjectRoot
    $out = & $pythonExe -c "import basic_scanner; print(basic_scanner.__version__)" 2>&1
    Pop-Location
    if ($LASTEXITCODE -eq 0 -and $out -match "^\d+\.\d+\.\d+") {
        Write-Host "  Import + version $($out.Trim()) [OK]" -ForegroundColor Green
        $importOk = $true
    }
} catch { Pop-Location }
if (-not $importOk) {
    Write-Host "  Import ou version [ÉCHEC]" -ForegroundColor Red
    Write-Host "    Exécutez : pip install -e ." -ForegroundColor Gray
    $failed++
}
Write-Host ""

# --- 3. Commande CLI basic_scanner ---
Write-Host "3. Commande CLI basic_scanner" -ForegroundColor White
$cliOk = $false
try {
    Push-Location $ProjectRoot
    $help = & $pythonExe -m basic_scanner.main --help 2>&1
    Pop-Location
    if ($LASTEXITCODE -eq 0 -and ($help -match "run|test-file")) {
        Write-Host "  basic_scanner --help [OK]" -ForegroundColor Green
        $cliOk = $true
    }
} catch { Pop-Location }
if (-not $cliOk) {
    Write-Host "  basic_scanner --help [ÉCHEC]" -ForegroundColor Red
    Write-Host "    Vérifiez que le package est installé : pip install -e ." -ForegroundColor Gray
    $failed++
}
Write-Host ""

# --- 4. Fichier de configuration ---
Write-Host "4. Configuration" -ForegroundColor White
$configPath = Join-Path $ProjectRoot "config.yaml"
if (Test-Path $configPath) {
    Write-Host "  config.yaml présent [OK]" -ForegroundColor Green
} else {
    Write-Host "  config.yaml absent [ATTENTION]" -ForegroundColor Yellow
    Write-Host "    Copiez config.example.yaml en config.yaml" -ForegroundColor Gray
}
Write-Host ""

# --- 5. Tests (optionnel) ---
if (-not $Quick) {
    Write-Host "5. Tests unitaires (pytest)" -ForegroundColor White
    try {
        Push-Location $ProjectRoot
        try {
            $testOut = & $pythonExe -m pytest tests/ -v --tb=line -q 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Host "  Tous les tests passés [OK]" -ForegroundColor Green
            } else {
                Write-Host "  Certains tests ont échoué [ÉCHEC]" -ForegroundColor Red
                $failed++
            }
        } finally {
            Pop-Location
        }
    } catch {
        Write-Host "  pytest non disponible ou échec [ATTENTION]" -ForegroundColor Yellow
        Write-Host "    Installez avec : pip install -e .[dev]" -ForegroundColor Gray
    }
    Write-Host ""
} else {
    Write-Host "5. Tests unitaires : ignorés (-Quick)" -ForegroundColor Gray
    Write-Host ""
}

# --- 6. Prérequis OCR (informatifs) ---
Write-Host "6. Prérequis OCR (optionnels pour l'application)" -ForegroundColor White
$tesseractOk = $false
try {
    $t = Get-Command tesseract -ErrorAction SilentlyContinue
    if ($t) { & tesseract --version 2>&1 | Out-Null; if ($LASTEXITCODE -eq 0) { $tesseractOk = $true } }
} catch {}
if ($tesseractOk) {
    Write-Host "  Tesseract [OK]" -ForegroundColor Green
} else {
    Write-Host "  Tesseract non trouvé (OCR désactivé sans lui)" -ForegroundColor Yellow
}

$gsOk = $false
foreach ($g in @("gswin64c", "gswin32c")) {
    try {
        if (Get-Command $g -ErrorAction SilentlyContinue) { $gsOk = $true; break }
    } catch {}
}
if ($gsOk) {
    Write-Host "  Ghostscript [OK]" -ForegroundColor Green
} else {
    Write-Host "  Ghostscript non trouvé (requis par ocrmypdf)" -ForegroundColor Yellow
}
Write-Host ""

# --- Bilan ---
Write-Host "=== Bilan ===" -ForegroundColor Cyan
if ($failed -eq 0) {
    Write-Host "Installation vérifiée avec succès." -ForegroundColor Green
    Write-Host "Vous pouvez lancer : basic_scanner run --config config.yaml" -ForegroundColor Gray
    exit 0
} else {
    Write-Host "Échec : $failed contrôle(s) en erreur. Corrigez puis relancez verify.ps1 ou install.ps1." -ForegroundColor Red
    exit 1
}
