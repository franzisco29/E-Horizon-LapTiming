# Ngrok Configuration - Consolidazione Sessioni

## Problema
Il tuo account ngrok free è limitato a **3 sessioni agent simultanee**. Stavi ricevendo errore:
```
Your account is limited to 3 simultaneous ngrok agent sessions.
```

## Soluzione Implementata
Ho consolidato tutti gli endpoint in **una singola sessione agent** usando un file di configurazione `ngrok.yml`.

### File Modificati
1. **`Classes/live_timing_hub.py`** - Modificato `_start_public_tunnel()` per usare `ngrok start --all` anziché `ngrok http`
2. **`ngrok.yml`** - Creato nel progetto (copia per documentazione)
3. **`~/.ngrok2/ngrok.yml`** - Creato nella home ngrok (configurazione attiva)

## Come Usare

### 1. Pulire le sessioni ngrok attive (IMPORTANTE)
Apri PowerShell e esegui:
```powershell
# Uccidi tutti i processi ngrok attivi
Get-Process ngrok -ErrorAction SilentlyContinue | Stop-Process -Force

# Verifica che siano tutti spenti
Get-Process ngrok -ErrorAction SilentlyContinue
```

### 2. Set dell'authtoken (se necessario)
Se non hai ancora configurato un authtoken, esegui:
```powershell
ngrok config add-authtoken <YOUR_NGROK_AUTHTOKEN>
```

Puoi trovare il tuo token su: https://dashboard.ngrok.com/auth/your-authtoken

### 3. Avviare l'applicazione
L'app avvierà automaticamente ngrok con la configurazione consolidata.

Se vuoi avviare ngrok manualmente:
```powershell
ngrok start --all
```

## Configurazione ngrok.yml

Il file `~/.ngrok2/ngrok.yml` contiene:

```yaml
version: 3
agent:
  authtoken: ${NGROK_AUTHTOKEN}
  
tunnels:
  live-timing:
    addr: 127.0.0.1:8000
    proto: http
    domain: alphonso-supersacerdotal-tomboyishly.ngrok-free.dev
    metadata: "Live Timing Hub"
```

### Aggiungere Ulteriori Tunnel
Se in futuro avrai bisogno di aggiungere altri endpoint, modifica `ngrok.yml`:

```yaml
tunnels:
  live-timing:
    addr: 127.0.0.1:8000
    proto: http
    domain: alphonso-supersacerdotal-tomboyishly.ngrok-free.dev
  
  nuovo-tunnel:
    addr: 127.0.0.1:8001
    proto: http
    domain: tuo-dominio-ngrok.ngrok-free.dev
```

Tutti i tunnel nella configurazione verranno avviati in **una singola sessione agent**.

## Specifiche Tecniche

- **Prima**: `ngrok http <url>` creava una sessione separata per ogni tunnel
- **Dopo**: `ngrok start --all` legge tutti i tunnels da `ngrok.yml` e li avvia in una sola sessione
- **Vantaggio**: Niente più errore di "3 simultaneous sessions limit"
- **Documentazione**: https://ngrok.com/docs/agent/config/

## Risoluzione Problemi

**Se ricevi ancora l'errore di sessioni?**
1. Verifica che non ci siano altre istanze di ngrok in esecuzione:
   ```powershell
   Get-Process ngrok
   ```
2. Uccidi tutte le istanze:
   ```powershell
   Get-Process ngrok -ErrorAction SilentlyContinue | Stop-Process -Force
   ```
3. Riavvia l'applicazione

**Se ngrok non si avvia?**
1. Verifica che ngrok sia installato:
   ```powershell
   ngrok version
   ```
2. Se non installato: `scoop install ngrok` o scarica da https://ngrok.com/download

**Se il dominio custom non funziona?**
- I domini custom richiedono un account a pagamento
- Su free tier puoi usare solo domini autogenerati (es: `eab1-12-34-56-78.ngrok-free.app`)
- Modifica `ngrok.yml` per rimuovere la linea `domain:` oppure aggiorna il dominio da https://dashboard.ngrok.com/domains
