@echo off
REM BASIC Scanner - Lancement de l'installation automatique (Windows)
REM Double-cliquez sur install.bat ou exécutez depuis une invite de commandes.

set "SCRIPT=%~dp0install.ps1"
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT%" %*
set EXIT=%ERRORLEVEL%
if not "%EXIT%"=="0" pause
exit /b %EXIT%
