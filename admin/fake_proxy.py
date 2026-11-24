import socket

HOST = "127.0.0.1"
PORTA = 5000

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORTA))
    server.listen()
    print(f"[FAKE PROXY] In ascolto su {HOST}:{PORTA}")

    while True:
        conn, indirizzo = server.accept()
        with conn:
            dati = conn.recv(4096).decode("utf-8")
            print(
                f"[FAKE PROXY] Da {indirizzo[0]} ho ricevuto: {dati.strip()}")
            conn.sendall("OK\n".encode("utf-8"))
