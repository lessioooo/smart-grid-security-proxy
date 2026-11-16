import socket
import json

HOST = "127.0.0.1"
PORT = 5000

messaggio = {"mittente": "tester", "target": "nodo1", "azione": "SET_VOLTAGE", "valore": "20000"}
dati = (json.dumps(messaggio) + "\n").encode("utf-8")

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(3)
try:
    sock.connect((HOST, PORT))
    sock.sendall(dati)
    print("Inviato, aspetto la risposta...")
    risposta = sock.recv(4096)
    if risposta:
        print("Risposta:", risposta)
    else:
        print("Il server ha chiuso la connessione senza rispondere")
except ConnectionRefusedError:
    print("Connessione rifiutata: il proxy non è acceso")
except socket.timeout:
    print("Nessuna risposta entro 3 secondi")
except OSError as e:
    print("Errore:", e)
finally:
    sock.close()