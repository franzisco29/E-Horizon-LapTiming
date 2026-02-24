import sys
from PySide6.QtWidgets import QApplication
from Modules.log_utils import log

# Assicurati che il percorso del file dove risiede HomeWindow sia corretto.
# Se HomeWindow si trova in un file chiamato 'home_window.py', usa:
# from UI.HomeWindow.home_window import HomeWindow
# (Adatta l'import qui sotto in base alla tua struttura cartelle)
from UI.HomeWindow.home_window import HomeWindow 

def main():
    log("--- Avvio Applicazione ---")
    
    # 1. Creazione dell'istanza QApplication
    # sys.argv permette di passare argomenti da riga di comando
    app = QApplication(sys.argv)
    
    # Opzionale: Impostazioni globali dell'applicazione
    app.setApplicationName("Race Manager System")
    app.setOrganizationName("YourProject")

    # 2. Inizializzazione della finestra principale
    try:
        window = HomeWindow()
        window.show()
        log("HomeWindow visualizzata con successo.")
    except Exception as e:
        log(f"ERRORE CRITICO durante l'avvio: {e}", level="ERROR")
        sys.exit(1)

    # 3. Esecuzione del loop degli eventi
    # sys.exit assicura che il codice di uscita di Qt venga passato al sistema operativo
    sys.exit(app.exec())

if __name__ == "__main__":
    main()