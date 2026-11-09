import threading
import time
import requests

IP_BANNATI = set()
FIRME_MALEVOLE = [] 
REGOLE_ELETTRICHE = {
    "SET_FREQUENCY": (49.5, 50.5),
    "SET_VOLTAGE": (18000, 22000),
    "SET_ACTIVE_POWER": (0, 500),
    "TRIP_BREAKER": (0, 1)
}

def refresh_banned_ips():
    while True:
        try:
            url = "https://rules.emergingthreats.net/fwrules/emerging-Block-IPs.txt" # usa lista di ip bannati di Emerging Threats
            response = requests.get(url, timeout = 10)

            IP_BANNATI.clear()  # Pulisce il set prima di aggiornare
            for riga in response.text.splitlines():
                if riga and not riga.startswith("#"):  # Ignora righe vuote e commenti
                    IP_BANNATI.add(riga.strip())

            print (f"[*] Lista IP bannati aggiornata. Totale IP bannati: {len(IP_BANNATI)}")
        except Exception as e:
            print(f"[!] Errore durante l'aggiornamento della lista IP bannati: {e}")

        time.sleep(86400)
    
  # Aggiorna ogni 24 ore
def is_ip_banned(ip):
    return ip in IP_BANNATI

def load_dinamic_signatures():

    print("[*] Caricamento firme malevole dinamiche...")
    url_minacce = [
        # SQL Injection (database)
        "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Fuzzing/SQLi/Quick-SQLi.txt",
        # Command Injection (sistemi operativi Linux/Windows)
        "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Fuzzing/command-injection-commmon.txt",
        # Local File Inclusion / Path Traversal (es. ../../ cartelle)
        "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Fuzzing/LFI/LFI-gracefulsecurity-linux.txt"
    ]
    FIRME_MALEVOLE.clear()  

    for url in url_minacce:
        nome_file = url.split("/")[-1] # estrae solo il nome del file per il print
        print(f"[*] Caricamento firme malevole da {nome_file}...")

        try:
            response = requests.get(url, timeout=10)

            for riga in response.text.splitlines():
                firma = riga.strip()
                if firma and not firma.startswith("#"):  # Ignora righe vuote e commenti
                    FIRME_MALEVOLE.append(firma)

        except Exception as e:
            print(f"[!] Errore durante il caricamento delle firme da {nome_file}: {e}")


    if not FIRME_MALEVOLE:
        print("[!] Tutte le connessioni fallite. Attivazione firme di fallback hardcodate.")
        FIRME_MALEVOLE.extend(["DROP TABLE", "SELECT", "UNION", "1=1", "; rm -rf", "/etc/passwd"])
    else:
        print(f"[*] Caricamento firme malevole completato. Totale firme caricate: {len(FIRME_MALEVOLE)}")
        
def is_payload_malicious(valore):
    valore_str = str(valore).upper()
    return any(firma.upper() in valore_str for firma in FIRME_MALEVOLE)

def valida_regola_fisica(azione, valore): 
    limit_consentiti = REGOLE_ELETTRICHE.get(azione)

    if limit_consentiti is None: # l'azione non è riconosciuta, comando illegittimo
        return False

    minimo, massimo = limit_consentiti # estrapola i valori minimi e massimi della tupla

    try: # messa in sicurezza del tipo di dato
        valore_numerico = float(valore) # se l'attaccante ha mandato un intero o una stringa numerica, funziona.
    except ValueError:
        return False  # il valore non è un numero

    if minimo <= valore_numerico <= massimo: # se il valore è compreso tra i limiti consentiti
        return True # tutto ok
    else:
        return False  # valore anomalo
