@echo off
REM Build BASIC Scanner en exécutable Windows (PyInstaller)
REM Prérequis : pip install pyinstaller (ou pip install -e ".[dev]")
cd /d "%~dp0"

python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo PyInstaller non trouvé. Installez-le avec : pip install pyinstaller
    exit /b 1
)

echo Construction de l'exécutable...
python -m PyInstaller --noconfirm basic_scanner.spec
if errorlevel 1 (
    echo Échec du build.
    exit /b 1
)

if exist "dist\BASIC Scanner.exe" (
    echo.
    echo Build terminé. Fichier : dist\BASIC Scanner.exe
    echo - Un seul fichier à télécharger / distribuer.
    echo - Au premier lancement, config.yaml est créé à côté de l'exe.
    echo - Tesseract et Ghostscript doivent être installés sur la machine pour l'OCR.
) else (
    echo Fichier dist\BASIC Scanner.exe introuvable après le build.
    exit /b 1
)
