import socket

def run_simulator():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_ip = '127.0.0.1'
    port = 5001
    server.bind((server_ip, port))
    server.listen(5)
    print(f"[SIMULATORE] sto ascoltando sulla port {server_ip}:{port} raga sempre al top senza stop")

    while True:
        client_sockt, addr = server.accept()
        data = client_sockt.recv(1024).decode('utf-8')
        if data:
            print(f"[SIMULATORE] ricevuto: {data}")
            client_sockt.sendall(f"Simulatore ha ricevuto: {data}".encode('utf-8'))
        client_sockt.close()
if __name__ == "__main__":
     run_simulator()
