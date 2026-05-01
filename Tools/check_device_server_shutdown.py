"""
Script di test per verificare che DeviceManager rilasci la porta TCP dopo disconnect_all().
Eseguirlo nell'ambiente dell'app (Python che ha PySide6 installato).
"""
import sys
import time
import socket
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PORT = 20777

try:
    from Classes.device_manager import DeviceManager, ConnectionTypes
except Exception as ex:
    print("ImportError durante import di DeviceManager:", ex)
    print("Assicurati di eseguire questo script con l'ambiente dell'app (PySide6 installato).")
    sys.exit(2)

print("Creazione DeviceManager...")
dm = DeviceManager(ip="0.0.0.0", port=PORT, conn_type=ConnectionTypes.TCP, debug_log=True, accept_timeout_s=1.0)
print("Avvio server...")
# start() è chiamato nel costruttore se conn_type == TCP

print("Attendo 1s...")
time.sleep(1)

print("Chiamo disconnect_all()...")
dm.disconnect_all()

print("Attendo 0.5s per lasciar terminare i thread...")
time.sleep(0.5)

# Proviamo a bind sulla stessa porta per verificare che sia libera
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", PORT))
    s.listen(1)
    print(f"SUCCESS: Porta {PORT} riassegnabile → server chiuso correttamente")
except Exception as ex:
    print(f"FAIL: Impossibile bindare porta {PORT}: {ex}")
finally:
    try:
        s.close()
    except Exception:
        pass

print("Test completato")
