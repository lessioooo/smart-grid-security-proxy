import sqlite3
import threading
lock = threading.Lock()
from datetime import datetime
# creazione database per il log degli ingressi dei pacchetti
def init_db():
    con = sqlite3.connect('nids_log.db')
    cur = con.cursor()
    cur.execute(""""
        CREATE TABLE IF NOT EXISTS allarmi(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            ip_sorgente TEXT NOT NULL,
            target TEXT NOT NULL,
            azione TEXT NOT NULL,
            motivo TEXT NOT NULL
    
        )
    """)
    con.commit()
    con.close()
# funzione che aggiunge al log gli ingressi malevoli
def log_allarme(ip_sorgente, target, azione, motivo):
    with lock: # Assicura che solo un thread alla volta possa accedere a questa sezione 
        con = None 
        try:
            timestamp_attuale = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            con = sqlite3.connect('nids_log.db')
            cur = con.cursor()
            cur.execute(
            "INSERT INTO allarmi (timestamp, ip_sorgente, target, azione, motivo) VALUES (?, ?, ?, ?, ?)",
            (timestamp_attuale, ip_sorgente, target, azione, motivo))
            con.commit()
        except sqlite3.Error as e:
            print(f"[!] Errore durante l'inserimento nel database: {e}")
        finally:
            if con:
                con.close()

if __name__ == "__main__":
    init_db()
    print("[*] Database SQLite inizializzato con successo in 'nids_log.db'")

