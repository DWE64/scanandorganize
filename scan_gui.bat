@echo off
REM BASIC Scanner - Lance l'interface sans fenêtre terminal (via VBS)
REM Double-cliquez sur scan_gui.bat pour ouvrir uniquement la fenêtre de l'application.

cd /d "%~dp0"
if exist "%~dp0scan_gui.vbs" (
    wscript.exe "%~dp0scan_gui.vbs"
) else (
    if exist ".venv\Scripts\pythonw.exe" (
        start "" ".venv\Scripts\pythonw.exe" "scan_gui.py"
    ) else (
        start "" "pythonw" "scan_gui.py"
    )
)
exit /b 0
