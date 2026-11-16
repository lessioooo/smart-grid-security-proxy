"""
FUZZ TEST - collaudo della gestione input malformati sul proxy NIDS (127.0.0.1:5000)

Manda una serie di pacchetti "anomali" (JSON rotto, campi mancanti,
tipi sbagliati, stringhe strane) e controlla come reagisce il server:
se risponde con un errore gestito, se non risponde, se chiude la
connessione, o se il server va in crash (in quel caso lo vedi nel suo
terminale, non in questo script).
"""

import socket
import json
import time

HOST = "127.0.0.1"
PORT = 5000


def invia_payload(payload_bytes, timeout=3):
    """
    Apre una connessione, manda i bytes passati così come sono
    (NON li tocca: possono anche non essere JSON valido) e
    restituisce (esito, dettaglio).
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((HOST, PORT))
        sock.sendall(payload_bytes)
        risposta = sock.recv(4096)
        if risposta:
            return "RISPOSTA", risposta.decode("utf-8", errors="replace")
        else:
            return "CHIUSA_SENZA_RISPOSTA", None
    except ConnectionRefusedError:
        return "RIFIUTATA", None
    except socket.timeout:
        return "TIMEOUT", None
    except OSError as e:
        return "ERRORE", str(e)
    finally:
        sock.close()


# ======================================================================
# CASI DI FUZZING
# Ogni voce è (nome del caso, bytes da inviare).
# Puoi aggiungerne altri seguendo lo stesso schema.
# ======================================================================

def costruisci_casi():
    casi = []

    # 1. JSON completamente rotto (sintassi non valida)
    casi.append(("JSON con sintassi rotta", b'{"mittente": "tester", "target":' ))

    # 2. JSON valido ma vuoto
    casi.append(("JSON vuoto", b'{}\n'))

    # 3. Campi mancanti (manca "azione" e "valore")
    casi.append(("Campi mancanti", json.dumps({"mittente": "tester", "target": "nodo1"}).encode("utf-8") + b"\n"))

    # 4. Tipi sbagliati (valore come numero invece che stringa, target come lista)
    casi.append(("Tipi di dato sbagliati", json.dumps(
        {"mittente": "tester", "target": ["nodo1", "nodo2"], "azione": "SET_VOLTAGE", "valore": 20000}
    ).encode("utf-8") + b"\n"))

    # 5. Valore numerico fuori da ogni scala plausibile
    casi.append(("Valore enorme", json.dumps(
        {"mittente": "tester", "target": "nodo1", "azione": "SET_VOLTAGE", "valore": "99999999999999999999"}
    ).encode("utf-8") + b"\n"))

    # 6. Valore negativo
    casi.append(("Valore negativo", json.dumps(
        {"mittente": "tester", "target": "nodo1", "azione": "SET_VOLTAGE", "valore": "-5000"}
    ).encode("utf-8") + b"\n"))

    # 7. Stringa non numerica dove ci si aspetta un numero
    casi.append(("Valore non numerico", json.dumps(
        {"mittente": "tester", "target": "nodo1", "azione": "SET_VOLTAGE", "valore": "abcde"}
    ).encode("utf-8") + b"\n"))

    # 8. Azione sconosciuta
    casi.append(("Azione inesistente", json.dumps(
        {"mittente": "tester", "target": "nodo1", "azione": "AZIONE_INVENTATA", "valore": "10"}
    ).encode("utf-8") + b"\n"))

    # 9. Stringa lunghissima (buffer / limiti di lettura)
    casi.append(("Stringa molto lunga", json.dumps(
        {"mittente": "A" * 10000, "target": "nodo1", "azione": "SET_VOLTAGE", "valore": "20000"}
    ).encode("utf-8") + b"\n"))

    # 10. Caratteri speciali / possibile injection nei campi testuali
    casi.append(("Caratteri speciali / injection", json.dumps(
        {"mittente": "'; DROP TABLE allarmi; --", "target": "nodo1", "azione": "SET_VOLTAGE", "valore": "20000"}
    ).encode("utf-8") + b"\n"))

    # 11. Pacchetto binario puro, non testo
    casi.append(("Bytes binari casuali", bytes([0, 1, 2, 255, 254, 253, 10])))

    # 12. Pacchetto vuoto (connessione aperta e chiusa subito)
    casi.append(("Pacchetto vuoto", b""))

    # 13. JSON valido ma non è un oggetto (è una lista)
    casi.append(("JSON che è una lista, non un oggetto", b'["mittente", "tester"]\n'))

    # 14. Numero mandato al posto di un oggetto JSON
    casi.append(("JSON che è solo un numero", b'12345\n'))

    # 15. Messaggio senza terminatore \n
    casi.append(("Senza terminatore newline", json.dumps(
        {"mittente": "tester", "target": "nodo1", "azione": "SET_VOLTAGE", "valore": "20000"}
    ).encode("utf-8")))  # niente \n finale

    return casi


def main():
    casi = costruisci_casi()
    print(f"[*] Avvio fuzz test: {len(casi)} casi\n")

    risultati = []
    for nome, payload in casi:
        esito, dettaglio = invia_payload(payload)
        risultati.append((nome, esito, dettaglio))
        riga = f"[{esito:22}] {nome}"
        if dettaglio:
            riga += f" -> {dettaglio[:120]}"
        print(riga)
        time.sleep(1.1)  # supera il RATE_LIMIT del proxy (1 secondo) tra un caso e l'altro

    # Riepilogo per esito
    print("\n===== RIEPILOGO FUZZ TEST =====")
    conteggi = {}
    for _, esito, _ in risultati:
        conteggi[esito] = conteggi.get(esito, 0) + 1
    for esito, n in conteggi.items():
        print(f"{esito:22}: {n}")


if __name__ == "__main__":
    main()