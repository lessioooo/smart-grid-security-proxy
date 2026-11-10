import socket
import json
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(('127.0.0.1', 5000))

data = {
    "mittente" : "mittenteProva",
    "target" : "targetProva",
    "azione" : "SET_VOLTAGE",
    "valore" : "18000",
    "ip_simulato" : "185.15.2.1"
}

payload_bites = json.dumps(data).encode('utf-8')
client.sendall(payload_bites)

print("[*] Dati inviati al server. In attesa di risposta...")

risposta = client.recv(1024)
print(f"[*] Risposta dal server: {risposta.decode('utf-8')}")
client.close()