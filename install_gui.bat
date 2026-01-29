@echo off
REM BASIC Scanner - Lance l'installateur sans fenêtre terminal
REM Double-cliquez sur install_gui.bat pour ouvrir uniquement la fenêtre d'installation.

cd /d "%~dp0"
if exist "%~dp0install_gui.vbs" (
    wscript.exe "%~dp0install_gui.vbs"
) else (
    pythonw install_gui.py 2>nul
    if errorlevel 1 python install_gui.py
)
exit /b 0
