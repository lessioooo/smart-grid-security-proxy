import socket

def run_proxy():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) 
    server.bind(('127.0.0.1', 5000))
    server.listen(5)
    print("[NIDS PROXY] In ascolto sulla porta 5000...")

    while True:
        client_sock, addr = server.accept()
        print(f"[NIDS PROXY] Connessione accettata da {addr}")
        data = client_sock.recv(1024).decode('utf-8')
        
        if data:
            print(f"[NIDS PROXY] Dati ricevuti dal client: {data}")
            
            if "MALICIOUS" in data:
                print("[NIDS PROXY] ATTACCO RILEVATO! Bloccato.")
                client_sock.sendall(b"ERRORE: Bloccato dal NIDS di sicurezza")
            else:
                print("[NIDS PROXY] Tentativo diinoltro al Simulatore (porta 5001)...")
                try:
                    sim_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sim_sock.connect(('127.0.0.1', 5001))
                    sim_sock.sendall(data.encode('utf-8'))
                    response = sim_sock.recv(1024)
                    sim_sock.close()
                    print("[NIDS PROXY] Risposta ricevuta dal Simulatore, la rimando al client.")
                    client_sock.sendall(response)
                except Exception as e:
                    print(f"[NIDS PROXY ERRORE] Impossibile connettersi al simulatore: {e}")
                    client_sock.sendall(b"ERRORE: Simulatore irraggiungibile")
                    
        client_sock.close()

if __name__ == "__main__":
    run_proxy()