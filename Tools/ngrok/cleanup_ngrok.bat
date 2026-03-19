@echo off
REM Ngrok Session Cleanup Script
REM Questo script uccide tutte le sessioni ngrok attive

echo.
echo ========================================
echo Ngrok Session Cleanup
echo ========================================
echo.

echo [*] Ricerca di processi ngrok attivi...
tasklist /FI "IMAGENAME eq ngrok.exe" 2>nul | find /I /N "ngrok.exe">nul
if "%ERRORLEVEL%"=="0" (
    echo [+] Trovati processi ngrok attivi. Uccisione in corso...
    taskkill /IM ngrok.exe /F /T
    echo [+] Processi ngrok terminati.
) else (
    echo [-] Nessun processo ngrok attivo trovato.
)

echo.
echo [*] Verifica finale...
tasklist /FI "IMAGENAME eq ngrok.exe" 2>nul | find /I /N "ngrok.exe">nul
if "%ERRORLEVEL%"=="0" (
    echo [-] Attenzione: Ancora processi ngrok attivi!
) else (
    echo [+] Tutti i processi ngrok sono stati terminati.
    echo [+] Puoi ora avviare l'applicazione con la nuova configurazione.
)

echo.
pause
