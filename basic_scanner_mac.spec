# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec pour BASIC Scanner sur macOS
# Build (sur Mac uniquement) : python -m PyInstaller --noconfirm basic_scanner_mac.spec
# Résultat : dist/BASIC Scanner.app (application Mac à distribuer)

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

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="BASIC Scanner",
    debug=False,
    strip=False,
    upx=True,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    name="BASIC Scanner",
)
