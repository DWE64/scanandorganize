# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec pour BASIC Scanner (exécutable Windows — un seul fichier)
# Build : python -m PyInstaller --noconfirm basic_scanner.spec
# Résultat : dist/BASIC Scanner.exe (un seul fichier à télécharger)

import os

SPECPATH = os.path.dirname(os.path.abspath(SPEC))

a = Analysis(
    [os.path.join(SPECPATH, "launcher.py")],
    pathex=[SPECPATH, os.path.join(SPECPATH, "src")],
    binaries=[],
    datas=[(os.path.join(SPECPATH, "config.example.yaml"), ".")],
    hiddenimports=[
        "scan_gui",
        "basic_scanner",
        "basic_scanner.main",
        "basic_scanner.config",
        "basic_scanner.watcher",
        "basic_scanner.extract",
        "basic_scanner.ocr",
        "basic_scanner.rules",
        "basic_scanner.mover",
        "basic_scanner.classify",
        "basic_scanner.suppliers",
        "basic_scanner.logging_conf",
        "basic_scanner.models",
        "watchdog",
        "watchdog.observers",
        "watchdog.observers.polling",
        "ocrmypdf",
        "pymupdf",
        "rapidfuzz",
        "yaml",
        "pytesseract",
        "PIL",
        "PIL.Image",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

# Un seul fichier .exe : tout est inclus dans l'exécutable
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    exclude_binaries=False,
    name="BASIC Scanner",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
