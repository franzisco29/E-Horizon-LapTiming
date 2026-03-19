# Ngrok Session Cleanup Script (PowerShell)
# Questo script uccide tutte le sessioni ngrok attive

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Ngrok Session Cleanup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[*] Ricerca di processi ngrok attivi..." -ForegroundColor Yellow
$ngrok_processes = Get-Process ngrok -ErrorAction SilentlyContinue

if ($ngrok_processes) {
    Write-Host "[+] Trovati $(($ngrok_processes | Measure-Object).Count) processo/i ngrok. Uccisione in corso..." -ForegroundColor Green
    $ngrok_processes | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 500
    Write-Host "[+] Processi ngrok terminati." -ForegroundColor Green
} else {
    Write-Host "[-] Nessun processo ngrok attivo trovato." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[*] Verifica finale..." -ForegroundColor Yellow
$remaining = Get-Process ngrok -ErrorAction SilentlyContinue

if ($remaining) {
    Write-Host "[-] Attenzione: Ancora processi ngrok attivi!" -ForegroundColor Red
} else {
    Write-Host "[+] Tutti i processi ngrok sono stati terminati." -ForegroundColor Green
    Write-Host "[+] Puoi ora avviare l'applicazione con la nuova configurazione." -ForegroundColor Green
}

Write-Host ""
Read-Host "Premi INVIO per chiudere..."
