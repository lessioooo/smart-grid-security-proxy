import threading
import time
import requests
import hmac
import hashlib
import os
from os import load_dotenv
load_dotenv()  # Carica le variabili d'ambiente dal file .env
IP_BANNATI = set()
FIRME_MALEVOLE = [] 
ULTIMI_SEQ_VISTI = {} 
REGOLE_ELETTRICHE = {
    "SET_FREQUENCY": (49.5, 50.5),
    "SET_VOLTAGE": (18000, 22000),
    "SET_ACTIVE_POWER": (0, 500),
    "TRIP_BREAKER": (0, 1)
}
# Dizionario delle zone intoccabili basato sulla topologia a 9 nodi
REGOLE_TOPOLOGICHE = {
    "ospedale": ["TRIP_BREAKER", "SHUTDOWN", "OFF", "DISCONNECT"],
    "centrale": ["SHUTDOWN", "OFF", "HALT"],
    "sottostazione_nord": ["SHUTDOWN", "OFF"],
    "sottostazione_sud": ["SHUTDOWN", "OFF"]
    # Le cabine residenziali, scolastiche, commerciali e sportive 
    # non sono qui perché possono subire distacchi legittimi.
}
MAPPA_CHIAVI = {
    "ospedale": "CHIAVE_OSPEDALE_NORD",
    "centrale": "CHIAVE_CENTRALE",
    "sottostazione_nord": "CHIAVE_SOTTOSTAZIONE_NORD",
    "sottostazione_sud": "CHIAVE_SOTTOSTAZIONE_SUD",
    "cabina_residenziale": "CHIAVE_CABINA_RESIDENZIALE",
    "cabina_scolastica": "CHIAVE_CABINA_SCOLASTICA",
    "cabina_commerciale": "CHIAVE_CABINA_COMMERCIALE",
    "cabina_sportiva": "CHIAVE_CABINA_SPORTIVA"
}

"""
la seguente funzione implementa l'autenticazione dei pacchetti SCADA tramite firme HMAC.
come funziona:
1. il mittente firma il pacchetto con una pre-shared key univoca caricata dal file .env.
2. il pacchetto deve contenere un 'timestamp'. se il pacchetto ha più di 5 secondi di ritardo, viene scartato (difesa base contro replay attack  ritardati).
3. ogni nodo deve incrementare un contatore 'seq' ad ogni invio. Il NIDS memorizza l'ultimo 'seq' valido. Se riceve un 'seq' minore o uguale, significa che un attaccante sta reinviando un pacchetto valido 
   catturato in precedenza. Il pacchetto viene droppato.
"""
def is_pacchetto_autentico(json_data):
    mittente = json_data.get("mittente")
    seq = json_data.get("seq")
    timestamp = json_data.get("timestamp")
    azione = json_data.get("azione")
    valore = json_data.get("valore")
    target = json_data.get("target")
    ip = json_data.get("ip_simulato")
    firma_ricevuta = json_data.get("firma")
    if not mittente:
        return False, "Pacchetto malformato: mittente assente"
    if mittente not in MAPPA_CHIAVI:
        return False, "Pacchetto malformato: mittente non riconosciuto"
        
    nome_variabile_chiave = MAPPA_CHIAVI[mittente]

    chiave_stringa = os.getenv(nome_variabile_chiave)
    if not chiave_stringa:
        return False, f"Errore Server: Chiave segreta per {mittente} non trovata nelle variabili d'ambiente"

    chiave_bytes = chiave_stringa.encode('utf-8')

    if seq is None or timestamp is None:
        return False, "Pacchetto malformato: seq o timestamp assente"
        
    # Cast obbligatorio per sicurezza (previene crash se il client li manda come stringhe)
    try:
        timestamp_float = float(timestamp)
        seq_int = int(seq)
    except ValueError:
        return False, "Pacchetto malformato: seq o timestamp non numerici"

    if abs(time.time() - timestamp_float) > 5.0:  # 5 secondi di tolleranza
        return False, "Pacchetto droppato: timestamp fuori dal range consentito (Replay Attack o orologi desincronizzati)"

    if not firma_ricevuta:
        return False, "Pacchetto malformato: firma HMAC assente"

    stringa_da_verificare = f"{mittente}|{seq}|{timestamp}|{azione}|{valore}|{target}|{ip}"
    messaggio_bytes = stringa_da_verificare.encode('utf-8')
    hash_calcolato = hmac.new(chiave_bytes, messaggio_bytes, hashlib.sha256).hexdigest()
    
    # Confronto a tempo costante per mitigare timing attack
    if not hmac.compare_digest(hash_calcolato, firma_ricevuta):
        return False, "Pacchetto droppato: firma non valida (Spoofing o Man-in-the-Middle)"
            
    ultimo_seq = ULTIMI_SEQ_VISTI.get(mittente, 0)
        
    if seq_int <= ultimo_seq:
        return False, f"Pacchetto droppato: sequence number non valido. Ricevuto {seq_int}, ultimo valido {ultimo_seq} (Replay Attack)"
        
    # a questo punto, il pacchetto ha superato tutto. 
    # aggiorno la memoria con l'ultimo seq valido e diamo l'ok.
    ULTIMI_SEQ_VISTI[mittente] = seq_int
        
    return True, "Pacchetto autentico"

def is_azione_bannata(azione, target):
    # Trasformo in minuscolo per evitare case-sensitivity (es. Ospedale vs ospedale)
    target_pulito = str(target).lower().strip()
    azione_pulita = str(azione).upper().strip()

    if target_pulito in REGOLE_TOPOLOGICHE:
        # Se l'azione richiesta è nella lista nera di quel target, blocca tutto
        if azione_pulita in REGOLE_TOPOLOGICHE[target_pulito]:
            return True
            
    return False


def refresh_banned_ips(): # funzione che aggiorna la lista di IP bannati da Emerging Threats ogni 24 ore
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
def is_ip_banned(ip): # controlla se l'IP è bannato
    return ip in IP_BANNATI

def load_dinamic_signatures(): # funzione che carica le firme malevole da fonti esterne

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
        
def is_payload_malicious(valore): # controlla se il payload contiene firme malevole
    valore_str = str(valore).upper()
    return any(firma.upper() in valore_str for firma in FIRME_MALEVOLE)

def valida_regola_fisica(azione, valore): # controlla se il valore è compreso tra i limiti consentiti per l'azione specificata
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

