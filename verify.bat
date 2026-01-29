@echo off
REM BASIC Scanner - Vérification de l'installation
REM Double-cliquez sur verify.bat ou exécutez : verify.bat
REM Code de sortie : 0 = OK, 1 = échec (à contrôler avec echo %ERRORLEVEL%)

set "SCRIPT=%~dp0verify.ps1"
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT%" %*
set EXIT=%ERRORLEVEL%
if not "%EXIT%"=="0" (
    echo.
    echo Verification echouee (code %EXIT%). Relancez install.ps1 si besoin.
    pause
)
exit /b %EXIT%
