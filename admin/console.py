import json
import socket

# Comandi disponibili nel menu.
# Bisogna sostituire i valori di "target" con i nomi veri usati dal plant e dal proxy.
COMANDI = {
    "1": {"descrizione": "Apri interruttore",  "target": "breaker_1", "azione": "open",  "valore": "0"},
    "2": {"descrizione": "Chiudi interruttore", "target": "breaker_1", "azione": "close", "valore": "1"},
}


def mostra_menu():
    print("\n=== ADMIN CONSOLE SCADA ===")
    for tasto, comando in COMANDI.items():
        print(f"{tasto}. {comando['descrizione']}")
    print("0. Esci")


def costruisci_comando(scelta):
    voce = COMANDI[scelta]
    return {
        "mittente": "admin",
        "target": voce["target"],
        "azione": voce["azione"],
        "valore": voce["valore"],
    }


def invia_comando(comando, host="127.0.0.1", porta=5000):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((host, porta))
            messaggio = json.dumps(comando) + "\n"
            s.sendall(messaggio.encode("utf-8"))
            risposta = s.recv(4096).decode("utf-8")
            return risposta.strip()
    except ConnectionRefusedError:
        return "ERRORE: impossibile connettersi al proxy (è acceso?)"


def main():
    while True:
        mostra_menu()
        scelta = input("Scelta: ").strip()

        if scelta == "0":
            print("Uscita.")
            break
        if scelta not in COMANDI:
            print("Scelta non valida, riprova.")
            continue

        comando = costruisci_comando(scelta)
        print("JSON da inviare:", json.dumps(comando))
        risposta = invia_comando(comando)
        print("Risposta del proxy:", risposta)


if __name__ == "__main__":
    main()
