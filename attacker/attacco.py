import socket #contiene tutto per la comunicazione di rete.
import json #serve a trasformare un dizionario Python in testo JSON
import time
import threading # serve per far girare più client contemporaneamente
HOST = "127.0.0.1"#l’indirizzo del server, come stringa (quindi tra virgolette). Il nostro è 127.0.0.1
PORT = 5000 #la porta, come numero intero (senza virgolette). La nostra è 5000

messaggio = {"mittente": "tester", "target": "nodo1", "azione": "lettura", "valore": "10"} #messaggio è il nome della scatola, le parole a sinistra sono le etichette, quelle a destra poi le cambio so test per mo
testo = json.dumps(messaggio) + "\n" #trasforma il testo in Jsone poi va a capo con la n
print(testo) #lo stampa
dati = testo.encode("utf-8") #trasforma il testo in byte
print(dati) #stampa uguale a prima ma con una b di byte

def invia_richieste(giri):
    inviati = 0
    rifiutati = 0
    timeouts = 0
    errori = 0
    i = 0
    while i < giri:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        try:
            sock.connect((HOST, PORT))
            sock.sendall(dati)
            sock.recv(1024)      # NUOVO: aspetta la risposta del server (max 5 secondi)
            inviati = inviati + 1
        except ConnectionRefusedError:
            rifiutati = rifiutati + 1
        except socket.timeout:
            timeouts = timeouts + 1
        except OSError as e:     # NUOVO: "as e" salva l'errore per poterlo stampare
            errori = errori + 1
            if errori == 1:
                print("Primo errore:", e)
        sock.close()
        i = i + 1
    return inviati, rifiutati, timeouts, errori


def lavoratore(numero, giri, risultati):
    risultati[numero] = invia_richieste(giri)
    print("Thread " + str(numero) + " finito\n", end="")   # NUOVO: evita le righe sovrapposte


NUM_THREAD = 25   # quanti client contemporanei
GIRI = 5         # quante richieste fa ciascun client

risultati = [None] * NUM_THREAD
thread = []

inizio = time.time()

for n in range(NUM_THREAD):
    t = threading.Thread(target=lavoratore, args=(n, GIRI, risultati))
    t.start()
    thread.append(t)

for t in thread:
    t.join()

durata = time.time() - inizio

inviati = 0
rifiutati = 0
timeouts = 0
errori = 0
for r in risultati:
    inviati = inviati + r[0]
    rifiutati = rifiutati + r[1]
    timeouts = timeouts + r[2]
    errori = errori + r[3]
totale = inviati + rifiutati + timeouts + errori

print("Thread:", NUM_THREAD)
print("Inviati:", inviati)
print("Rifiutati:", rifiutati)
print("Timeout:", timeouts)
print("Altri errori:", errori)
print("Durata (secondi):", durata)
print("Totale tentativi:", totale)
print("Richieste al secondo:", totale / durata)