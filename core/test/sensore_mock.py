import socket
import json
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(('127.0.0.1', 5000))

data = {
    "mittente" : "mittenteProva",
    "target" : "targetProva",
    "azione" : "SET_VOLTAGE",
    "valore" : "120",
    "ip_simulato" : "185.15.2.1"
}

payload_bites = json.dumps(data).encode('utf-8')
client.sendall(payload_bites)

print("[*] Data sent to the server. Wainting for response...")

risposta = client.recv(1024)
print(f"[*] Response from server: {risposta.decode('utf-8')}")
client.close()