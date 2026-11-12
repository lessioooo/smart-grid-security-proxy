import socket

HOST = "127.0.0.1"
PORT = 5000

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind((HOST, PORT))
server.listen(128)
print("Server finto in ascolto sulla porta", PORT)

ricevuti = 0
errori = 0
while True:
    try:
        conn, indirizzo = server.accept()
    except OSError as errore:
        print("Errore su accept:", errore)
        continue

    try:
        conn.settimeout(2)
        dati = conn.recv(4096)
        ricevuti = ricevuti + 1
        if ricevuti % 100 == 0:
            print("Ricevuti:", ricevuti, "Errori:", errori)
    except OSError as errore:
        errori = errori + 1
        print("Errore su connessione:", errore)
    finally:
        conn.close()