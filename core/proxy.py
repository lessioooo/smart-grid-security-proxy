import socket
import threading
import json
import time
from security_engine import IP_BANNATI, FIRME_MALEVOLE, REGOLE_ELETTRICHE, is_ip_banned, is_payload_malicious, valida_regola_fisica, load_dinamic_signatures, refresh_banned_ips, is_azione_bannata, is_pacchetto_autentico
from logger import log_allarme
HOST = '127.0.0.1'
PORT = 5000
RATE_LIMIT = 1.0 
IP_TRACKER = {}

def connection_handler(client_socket, address):
    ip_source = address[0]
    print(f"[*] Connessione stabilita con {ip_source}")

    try: 
        dati_grezzi = client_socket.recv(4096)

        if not dati_grezzi:
            return

        data = dati_grezzi.decode('utf-8')
        tempo_attuale = time.time()
        ultimo_accesso = IP_TRACKER.get(ip_source, 0) # Prende l'ultimo accesso, o 0 se è la prima volta
        IP_TRACKER[ip_source] = tempo_attuale
        # controllo se l'IP che cerca di connettersi supera il limite di connessioni per secondo
        if ip_source in IP_TRACKER: 
            if tempo_attuale - ultimo_accesso < RATE_LIMIT: 
                print(f"[!] Connessione da {ip_source} rifiutata per rate limiting.")
                log_allarme(ip_source, "N/A", "N/A", "Rate limiting")  # Log dell'evento di rate limiting
                client_socket.sendall(f"[!] Connessione rifiutata per rate limiting.".encode('utf-8'))
                return
                    
        json_data = json.loads(data) 
        # type checking anti fuzzing: controllo che il pacchetto ricevuto sia un dizionario JSON valido
        if not isinstance(json_data, dict):
            print(f"[!] Pacchetto JSON non valido ricevuto da {ip_source}. Ignorato.")
            log_allarme(ip_source, "N/A", "N/A", "Pacchetto JSON non valido")  # Log dell'evento di pacchetto JSON non valido
            client_socket.sendall(f"[!] ERRORE: PACCHETTO_JSON_NON_VALIDO".encode('utf-8'))
            return
        # estraggo i campi dal JSON ricevuto, con valori di default se non presenti
        mittente = str(json_data.get("mittente", "Sconosciuto")).strip().upper()
        azione = str(json_data.get("azione", "NESSUNA")).strip().upper()
        target = str(json_data.get("target", "Sconosciuto")).strip().upper()
        valore = json_data.get("valore", "0")
        try:
            valore = float(valore)
        except (ValueError, TypeError):
            print(f"[!] Valore non numerico ricevuto da {ip_source}. Ignorato.")
            log_allarme(ip_source, target, "Fuzzing Type", "Il parametro valore non è un numero")
            client_socket.sendall(f"[!] ERRORE: VALORE_NON_NUMERICO".encode('utf-8'))
            return
  

        if len(mittente) > 50 or len(target) > 50:
            print(f"[!] Pacchetto con mittente o target troppo lungo ricevuto da {ip_source}. Ignorato.")
            log_allarme(ip_source, target, azione, "Pacchetto con mittente o target troppo lungo")
            client_socket.sendall(f"[!] ERRORE: MITTENTE_O_TARGET_TROPPO_LUNGO".encode('utf-8'))
            return
        
 
        # serie di stateful inspection per controllare se il pacchetto ricevuto è malevolo o meno
        if is_ip_banned(ip_source): # controllo su ip bannati
            print(f"[!] Connessione da IP bannato: {ip_source}. Connessione terminata.")
            log_allarme(ip_source, target, azione, "IP bannato") # aggiunge al database l'ingresso malevolo
            client_socket.sendall(f"[!] Connessione da IP bannato: {ip_source}. Connessione terminata.".encode('utf-8'))
            return
        
        esito_hmac, messaggio_errore_hmac = is_pacchetto_autentico(json_data)
        if not esito_hmac:
            print(f"[!] Blocco Crittografico da {ip_source}: {messaggio_errore_hmac}")
            log_allarme(ip_source, target, azione, f"Fallimento HMAC: {messaggio_errore_hmac}")
            client_socket.sendall(f"[!] Connessione terminata: {messaggio_errore_hmac}".encode('utf-8'))
            return
        
        if is_payload_malicious(valore): # controllo su payload malevoli
            print(f"[!] Payload malevolo rilevato da {ip_source}. Connessione terminata.")
            log_allarme(ip_source, target, azione, "Payload malevolo")
            client_socket.sendall(f"[!] Payload malevolo rilevato da {ip_source}. Connessione terminata.".encode('utf-8'))
            return
        
        if not valida_regola_fisica(azione, valore): # controllo su valori fisici superati
            print(f"[!] BLOCCO ANOMALIA: Violazione limiti fisici (Azione: {azione}, Valore: {valore}).")
            log_allarme(ip_source, target, azione, "Violazione limiti fisici")
            client_socket.sendall(f"[!] BLOCCO ANOMALIA: Violazione limiti fisici (Azione: {azione}, Valore: {valore}).".encode('utf-8'))
            return
        
        if is_azione_bannata(azione, target): # controllo su azioni bannate
            print(f"[!] Tentativo di azione bannata (Azione: {azione}, Target: {target}).") 
            log_allarme(ip_source, target, azione, "Azione bannata") 
            client_socket.sendall(f"[!] Tentativo di azione bannata (Azione: {azione}, Target: {target}).".encode('utf-8'))
            return
        
        print(f"[+] Pacchetto da {mittente} sicuro. Aperta connessione verso il plant.")
        
        # costruisco un nuovo json ridotto con solo i campi necessari per il plant
        dati_ridotti= {
            "target": target,
            "azione": azione,
            "valore": valore
        }
        dati_per_plant = json.dumps(dati_ridotti).encode('utf-8')
        simulatore_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
        simulatore_socket.connect((HOST, PORT + 1))
        # inoltro il JSON pulito 
        simulatore_socket.sendall(dati_per_plant)
        risposta_simulatore = simulatore_socket.recv(1024)
        simulatore_socket.close()

        # rimando la risposta indetro al mittente che ha iniziato la comunicazione
        client_socket.sendall(risposta_simulatore)
        print(f"[+] Risposta del plant recapitata a {mittente}.")

    except json.JSONDecodeError:
        #  catturo pacchetti non-json e li ignoro
        print(f"[!] Pacchetto non JSON ricevuto da {ip_source}. Ignorato.")
        log_allarme(ip_source, "N/A", "N/A", "Pacchetto non JSON")  # Log dell'evento di pacchetto non JSON

    except Exception as e:
        print(f"[!] Errore durante la gestione della connessione da {ip_source}: {e}")
        log_allarme(ip_source, "N/A", "N/A", f"Errore interno: {e}")  # Log dell'errore interno

    finally:
        client_socket.close()
    print(f"[*] Connessione con {ip_source} chiusa.")


def start_nids():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #creato socket tcp con protocollo IPv4

    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server_socket.bind((HOST, PORT)) # associo socket a indirizzo e porta, in questo caso 127.0.0.1 e 5000

        server_socket.listen(5) # metto in ascolto per le prossime 5 connessioni in entrata
        print(f"[*] NIDS listening on {HOST}:{PORT}")

        while True: 
            client_socket, address = server_socket.accept() # programma si blocca fino a quando non arriva una connessione in entrata
            print(f"[*] Connessione ricevuta da {address}")
            thread = threading.Thread(target=connection_handler, args=(client_socket, address)) #creazione e avvuio del thread per gestire la connessione in entrata
            thread.start()
            print(f"[*] Connessioni attive: {threading.active_count() - 1}")

    except KeyboardInterrupt:
        print("\n[!] Chiusura del NIDS...") # così con ctrl+c si chiude il programma senza errori
    finally:
        server_socket.close()   

if __name__ == "__main__":

    load_dinamic_signatures()  # Carica le firme malevole dinamiche all'avvio
    thread_ip = threading.Thread(target=refresh_banned_ips, daemon=True)  # Thread per aggiornare gli IP bannati
    thread_ip.start()  # Avvia il thread per aggiornare gli IP bannati
    
    start_nids()
