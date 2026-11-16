"""
LOAD TEST - collaudo di carico sul proxy NIDS (127.0.0.1:5000)

Apre NUM_THREAD client simultanei, ognuno manda GIRI richieste JSON valide
al proxy, e misura quante vengono accettate, bloccate (rate limiting /
anomalia), rifiutate o scadute per timeout.
"""

import socket
import json
import time
import threading

HOST = "127.0.0.1"
PORT = 5000

# Messaggio valido secondo le REGOLE_ELETTRICHE del proxy
# (SET_VOLTAGE accetta un valore tra 18000 e 22000)
MESSAGGIO = {"mittente": "tester", "target": "nodo1", "azione": "SET_VOLTAGE", "valore": "20000"}
DATI = (json.dumps(MESSAGGIO) + "\n").encode("utf-8")

# Impostazioni del test: cambia questi due numeri per variare il carico
NUM_THREAD = 5
GIRI = 10


def invia_richieste(giri):
    """
    Esegue 'giri' connessioni in sequenza verso il proxy.
    Ritorna una tupla con il conteggio di ogni possibile esito.
    """
    inviati = 0     # richiesta accettata davvero dal sistema
    bloccati = 0    # risposta con "rifiutata" (rate limiting) o "BLOCCO" (anomalia)
    rifiutati = 0   # connessione TCP rifiutata (nessuno in ascolto)
    timeouts = 0    # nessuna risposta entro il timeout
    errori = 0      # altri errori di rete (es. porte esaurite)

    for _ in range(giri):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        try:
            sock.connect((HOST, PORT))
            sock.sendall(DATI)
            risposta = sock.recv(1024)
            if b"rifiutata" in risposta or b"BLOCCO" in risposta:
                bloccati += 1
            else:
                inviati += 1
        except ConnectionRefusedError:
            rifiutati += 1
        except socket.timeout:
            timeouts += 1
        except OSError:
            errori += 1
        finally:
            sock.close()

    return inviati, bloccati, rifiutati, timeouts, errori


def lavoratore(numero, giri, risultati):
    """Eseguito da ogni thread: chiama invia_richieste e salva il risultato."""
    risultati[numero] = invia_richieste(giri)


def main():
    risultati = [None] * NUM_THREAD
    thread = []

    print(f"[*] Avvio load test: {NUM_THREAD} thread x {GIRI} richieste = {NUM_THREAD * GIRI} totali")
    inizio = time.time()

    for n in range(NUM_THREAD):
        t = threading.Thread(target=lavoratore, args=(n, GIRI, risultati))
        t.start()
        thread.append(t)

    for t in thread:
        t.join()

    durata = time.time() - inizio

    inviati = sum(r[0] for r in risultati)
    bloccati = sum(r[1] for r in risultati)
    rifiutati = sum(r[2] for r in risultati)
    timeouts = sum(r[3] for r in risultati)
    errori = sum(r[4] for r in risultati)
    totale = inviati + bloccati + rifiutati + timeouts + errori

    print("\n===== REPORT LOAD TEST =====")
    print(f"Thread                : {NUM_THREAD}")
    print(f"Totale tentativi      : {totale}")
    print(f"  Inviati (accettati) : {inviati}")
    print(f"  Bloccati (rate limit/anomalia): {bloccati}")
    print(f"  Rifiutati (TCP)     : {rifiutati}")
    print(f"  Timeout             : {timeouts}")
    print(f"  Altri errori        : {errori}")
    print(f"Durata (secondi)      : {durata:.3f}")
    if durata > 0:
        print(f"Richieste al secondo  : {totale / durata:.1f}")


if __name__ == "__main__":
    main()