import socket
import threading
import json
from security_engine import IP_BANNATI, FIRME_MALEVOLE, REGOLE_ELETTRICHE, is_ip_banned, is_payload_malicious, valida_regola_fisica, load_dinamic_signatures, refresh_banned_ips 
HOST = '127.0.0.1'
PORT = 5000

def connection_handler(client_socket, address):
    ip_source = address[0]
    print(f"[*] Connessione stabilita con {ip_source}")

    try: 
        dati_grezzi = client_socket.recv(1024)

        if not dati_grezzi:
            return

        data = dati_grezzi.decode('utf-8')
        json_data = json.loads(data)

        mittente = json_data.get("mittente", "Sconosciuto")
        ip_simulato = json_data.get("ip_simulato", ip_source)
        azione = json_data.get("azione", "")
        valore = json_data.get("valore", "")

        if is_ip_banned(ip_simulato):
            print(f"[!] Connessione da IP bannato: {ip_simulato}. Connessione terminata.") # controllo su ip
            return
        if is_payload_malicious(valore):
            print(f"[!] Payload malevolo rilevato da {ip_simulato}. Connessione terminata.") # controllo su payload
            return
        if not valida_regola_fisica(azione, valore):
            print(f"[!] BLOCCO ANOMALIA: Violazione limiti fisici (Azione: {azione}, Valore: {valore}).") # controllo su regole fisiche
            return
        print(f"[+] Pacchetto da {mittente} sicuro. Aperta connessione verso il Simulatore.")
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
            print(f"[*] Connection received from {address}")
            thread = threading.Thread(target=connection_handler, args=(client_socket, address)) #creazione e avvuio del thread per gestire la connessione in entrata
            thread.start()
            print(f"[*] Active connections: {threading.active_count() - 1}")

    except KeyboardInterrupt:
        print("\n[!] Shutting down NIDS...") # così con ctrl+c si chiude il programma senza errori
    finally:
        server_socket.close()   

if __name__ == "__main__":

    load_dinamic_signatures()  # Carica le firme malevole dinamiche all'avvio
    thread_ip = threading.Thread(target=refresh_banned_ips, daemon=True)  # Thread per aggiornare gli IP bannati
    thread_ip.start()  # Avvia il thread per aggiornare gli IP bannati
    
    start_nids()