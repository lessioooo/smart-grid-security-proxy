import socket
import threading
import json
import time
from security_engine import IP_BANNATI, FIRME_MALEVOLE, REGOLE_ELETTRICHE, is_ip_banned, is_payload_malicious, valida_regola_fisica, load_dinamic_signatures, refresh_banned_ips, is_azione_bannata
from logger import log_allarme
HOST = '127.0.0.1'
PORT = 5000
RATE_LIMIT = 1.0 
IP_TRACKER = {}

def connection_handler(client_socket, address):
    ip_source = address[0]
    print(f"[*] Connessione stabilita con {ip_source}")

    try: 
        dati_grezzi = client_socket.recv(1024)

        if not dati_grezzi:
            return

        data = dati_grezzi.decode('utf-8')
        json_data = json.loads(data)
        # estraggo i campi dal JSON ricevuto, con valori di default se non presenti
        mittente = json_data.get("mittente", "Sconosciuto")
        ip_simulato = json_data.get("ip_simulato", ip_source)
        azione = json_data.get("azione", "nessuna")
        valore = json_data.get("valore", "0")
        target = json_data.get("target", "Sconosciuto")  

        tempo_attuale = time.time()
        if ip_simulato in IP_TRACKER: # controllo se l'IP che cerca di connettersi supera il limite di connessioni per secondo
            if tempo_attuale- IP_TRACKER[ip_simulato] < RATE_LIMIT:
                print(f"[!] Connessione da {ip_simulato} rifiutata per rate limiting.")
                log_allarme(ip_simulato, "N/A", "N/A", "Rate limiting")  # Log dell'evento di rate limiting
                client_socket.sendall(f"[!] Connessione rifiutata per rate limiting.".encode('utf-8'))
                return
        IP_TRACKER[ip_simulato] = tempo_attuale
 
        # serie di stateful inspection per controllare se il pacchetto ricevuto è malevolo o meno
        if is_ip_banned(ip_simulato): # controllo su ip bannati
            print(f"[!] Connessione da IP bannato: {ip_simulato}. Connessione terminata.")
            log_allarme(ip_simulato, target, azione, "IP bannato") # aggiunge al database l'ingresso malevolo
            client_socket.sendall(f"[!] Connessione da IP bannato: {ip_simulato}. Connessione terminata.".encode('utf-8'))
            return
        if is_payload_malicious(valore): # controllo su payload malevoli
            print(f"[!] Payload malevolo rilevato da {ip_simulato}. Connessione terminata.")
            log_allarme(ip_simulato, target, azione, "Payload malevolo")
            client_socket.sendall(f"[!] Payload malevolo rilevato da {ip_simulato}. Connessione terminata.".encode('utf-8'))
            return
        if not valida_regola_fisica(azione, valore): # controllo su valori fisici superati
            print(f"[!] BLOCCO ANOMALIA: Violazione limiti fisici (Azione: {azione}, Valore: {valore}).")
            log_allarme(ip_simulato, target, azione, "Violazione limiti fisici")
            client_socket.sendall(f"[!] BLOCCO ANOMALIA: Violazione limiti fisici (Azione: {azione}, Valore: {valore}).".encode('utf-8'))
            return
        if is_azione_bannata(azione, target): # controllo su azioni bannate
            print(f"[!] Tentativo di azione bannata (Azione: {azione}, Target: {target}).") 
            log_allarme(ip_simulato, target, azione, "Azione bannata") 
            client_socket.sendall(f"[!] Tentativo di azione bannata (Azione: {azione}, Target: {target}).".encode('utf-8'))
            return
        print(f"[+] Pacchetto da {mittente} sicuro. Aperta connessione verso il plant.")
        # creo un nuovo socket per parlare con il plant sulla porta 5001
        simulatore_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
        simulatore_socket.connect((HOST, PORT + 1))
        # inoltro i dati originali
        simulatore_socket.sendall(dati_grezzi)
        # attendo risposta dal plant
        risposta_simulatore = simulatore_socket.recv(1024)
        # chiudo il socket 
        simulatore_socket.close()

        # rimando la risposta indetro al mittente che ha iniziato la comunicazione
        client_socket.sendall(risposta_simulatore)
        print(f"[+] Risposta del plant recapitata a {mittente}.")

    except json.JSONDecodeError:
        #  catturo pacchetti non-json e li ignoro
        print(f"[!] Pacchetto non JSON ricevuto da {ip_source}. Ignorato.")

    except Exception as e:
        print(f"[!] Errore durante la gestione della connessione da {ip_source}: {e}")

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
