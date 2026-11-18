import socket
import json
import threading


def invia(target, valore):
    """Manda un comando al twin e restituisce la risposta come dizionario."""
    comando = {"target": target, "azione": "TRIP_BREAKER", "valore": valore}
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
        client.connect(("127.0.0.1", 5001))
        client.sendall(json.dumps(comando).encode("utf-8"))
        return json.loads(client.recv(4096).decode("utf-8"))


risultati = []  # qui ogni thread salva il suo esito


def lavoratore():
    # Ogni thread apre e chiude lo stesso interruttore, come farebbe un flooding
    for _ in range(20):
        risposta = invia("cabina_sportiva", "1")
        risultati.append(risposta["status"])
        risposta = invia("cabina_sportiva", "0")
        risultati.append(risposta["status"])


# Crea 50 thread che lavorano tutti insieme sul twin
thread = [threading.Thread(target=lavoratore) for _ in range(50)]
for t in thread:
    t.start()    # li fa partire tutti
for t in thread:
    t.join()     # aspetta che finiscano tutti

# 50 thread x 20 giri x 2 comandi = 2000 risposte, tutte SUCCESS
print("Risposte totali:", len(risultati))
print("Di cui SUCCESS:", risultati.count("SUCCESS"))