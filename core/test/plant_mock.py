import socket

IP = '127.0.0.1'
PORT = 5001
# creo un socket in ascolto su port 5001
socket_plant = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
socket_plant.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
socket_plant.bind((IP, PORT))
socket_plant.listen(5)

while True: 
    connessione, indirizzo = socket_plant.accept()
    risposta = connessione.recv(1024)
    print(f"[+] Pacchetto ricevuto dal proxy: {risposta.decode('utf-8')}.")
    connessione.sendall(b"Risposta dal plant: Pacchetto ricevuto correttamente.")
    connessione.close()
