import socket
def send_command(message):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        attacker_ip = '127.0.0.1'
        attacker_port = 5000
        client.connect((attacker_ip, attacker_port))
        client.sendall(message.encode('utf-8'))
        response = client.recv(1024).decode('utf-8')
        print(f"[ATTACKER] ricevuto: {response}")
    finally:
        client.close()

if __name__ == "__main__":
    # Invia un comando normale al proxy
    print("[ATTACKER] Inviando comando normale al proxy...")
    send_command("{azione: CHIUDI_INTERRUTTORE, nodo:1}")

    # Invia un comando malevolo al proxy
    print("[ATTACKER] Inviando comando malevolo al proxy... (packet injection)")
    send_command("MALICIOUS_PAYLOAD_OVERLOAD")

