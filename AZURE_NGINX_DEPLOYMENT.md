# Azure VM + Nginx Deployment

Il live timing ora ascolta direttamente su `0.0.0.0` e sulla porta configurata in `Modules/config_manager.py`. In produzione l'esposizione esterna va fatta con Nginx come reverse proxy sulla VM Azure.

## Flusso previsto

1. L'app Python parte sulla VM e apre il server live sulla porta configurata, ad esempio `8888`.
2. Nginx riceve le richieste su `80` e `443`.
3. Nginx inoltra tutto al backend locale `127.0.0.1:<porta_live>`.
4. La VM espone solo Nginx verso Internet; la porta dell'app resta interna.

## Esempio di configurazione Nginx

```nginx
server {
    listen 80;
    server_name your-domain.example.com;

    location / {
        proxy_pass http://127.0.0.1:8888;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 3600;
    }
}
```

Se la porta live cambia nella configurazione, aggiorna solo il `proxy_pass` con la nuova porta.

## Note operative

- Lascia la porta dell'app configurabile dalle impostazioni.
- Non usare tunnel esterni come ngrok o pyngrok.
- Apri nel NSG/Azure firewall solo le porte necessarie per Nginx, non la porta interna dell'app se il backend resta locale.
- Se usi HTTPS, termina il TLS su Nginx e continua a inoltrare al backend in HTTP locale.

## Verifica rapida

- Avvia l'app e controlla che il log indichi l'ascolto su `0.0.0.0:<porta>`.
- Verifica che `curl http://127.0.0.1:<porta>/api/snapshot` risponda sulla VM.
- Verifica che il dominio pubblico risponda tramite Nginx.