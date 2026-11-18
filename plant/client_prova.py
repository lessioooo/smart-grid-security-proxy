import socket
import json


def invia(payload):
    """Manda un messaggio (in byte) al twin e stampa la risposta."""
    # Crea il socket lato CLIENTE (stesso tipo di quello del server)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
        # Si collega al twin: "bussa" alla porta 5001 della nostra macchina
        client.connect(("127.0.0.1", 5001))

        # Manda i byte al server
        client.sendall(payload)

        # Aspetta la risposta (massimo 4096 byte) e la stampa come testo
        risposta = client.recv(4096)
        print(risposta.decode("utf-8"))


# Un comando valido: apre la sottostazione nord (valore "1" = APERTO)
comando_valido = {"target": "sottostazione_nord", "azione": "TRIP_BREAKER", "valore": "1"}

# dizionario -> testo JSON -> byte, perche' la rete trasporta solo byte
invia(json.dumps(comando_valido).encode("utf-8"))

# JSON rotto: il twin deve rispondere JSON_NON_VALIDO
invia(b'{pippo')

# Byte che non sono UTF-8 valido: il twin non deve crashare
# (la "b" davanti indica byte e non testo)
invia(b'\xff\xfe\x00')