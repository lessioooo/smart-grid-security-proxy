"""
EDGE-CASE LOGIC TEST - collaudo della logica di stato sul proxy NIDS (127.0.0.1:5000)

Non manda input "rotti" (quello lo fa fuzz.py): manda comandi JSON
perfettamente validi nella forma, ma messi ai limiti dei range ammessi
o in sequenze logicamente sospette, per vedere se il sistema controlla
la COERENZA dei comandi nel tempo, o se si limita a validare ogni
messaggio da solo, senza ricordare nulla di quello che è successo prima.
"""

import socket
import json
import time

HOST = "127.0.0.1"
PORT = 5000

# Stessi range che hai letto in REGOLE_ELETTRICHE dentro security_engine.py
RANGE = {
    "SET_FREQUENCY": (49.5, 50.5),
    "SET_VOLTAGE": (18000, 22000),
    "SET_ACTIVE_POWER": (0, 500),
    "TRIP_BREAKER": (0, 1),
}


def invia(messaggio, timeout=3):
    """Manda un messaggio (dict) e ritorna la risposta testuale del proxy, o None."""
    dati = (json.dumps(messaggio) + "\n").encode("utf-8")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((HOST, PORT))
        sock.sendall(dati)
        risposta = sock.recv(1024)
        return risposta.decode("utf-8", errors="replace") if risposta else None
    except OSError as e:
        return f"ERRORE: {e}"
    finally:
        sock.close()
        time.sleep(1.1)  # supera il RATE_LIMIT (1s) tra un invio e l'altro


def accettato(risposta):
    """True se il proxy ha inoltrato il comando al plant (non bloccato)."""
    return risposta is not None and "Risposta dal plant" in risposta


# ======================================================================
# PARTE 1: valori ESATTAMENTE al limite di ogni range
# Vogliamo sapere se il confine è incluso o escluso, e se è coerente
# tra tutte le azioni (es. 18000 passa ma 22000 no? sarebbe un'asimmetria).
# ======================================================================

def test_confini():
    print("--- PARTE 1: valori al confine di ogni range ---")
    for azione, (minimo, massimo) in RANGE.items():
        # scendiamo/saliamo di una unità piccola rispetto al range (1 o 0.1)
        passo = 0.1 if isinstance(minimo, float) else 1

        casi = [
            ("appena sotto il minimo", minimo - passo),
            ("al minimo esatto", minimo),
            ("al massimo esatto", massimo),
            ("appena sopra il massimo", massimo + passo),
        ]
        for descrizione, valore in casi:
            messaggio = {"mittente": "tester", "target": "nodo1", "azione": azione, "valore": str(valore)}
            risposta = invia(messaggio)
            esito = "ACCETTATO" if accettato(risposta) else "BLOCCATO"
            print(f"[{azione:17}] {descrizione:24} (valore={valore:>10}) -> {esito}")


# ======================================================================
# PARTE 2: sequenze logicamente sospette
# Ogni comando preso da solo è valido. Il dubbio è se il sistema
# controlla la coerenza TRA comandi successivi, o se li tratta sempre
# come eventi isolati senza nessuna memoria di stato.
# ======================================================================

def test_sequenze():
    print("\n--- PARTE 2: sequenze logiche sospette ---")

    # Caso A: apro l'interruttore (TRIP_BREAKER=1, nodo scollegato)
    # e SUBITO DOPO mando un comando di tensione sullo stesso nodo.
    # Un sistema "intelligente" dovrebbe rifiutare un comando elettrico
    # su un nodo appena disconnesso. Vediamo se lo fa.
    print("Caso A: TRIP_BREAKER=1 seguito da SET_VOLTAGE sullo stesso nodo")
    r1 = invia({"mittente": "tester", "target": "nodo1", "azione": "TRIP_BREAKER", "valore": "1"})
    print(f"  1) Apro interruttore nodo1          -> {'ACCETTATO' if accettato(r1) else 'BLOCCATO'}")
    r2 = invia({"mittente": "tester", "target": "nodo1", "azione": "SET_VOLTAGE", "valore": "20000"})
    print(f"  2) Imposto tensione su nodo1 scollegato -> {'ACCETTATO' if accettato(r2) else 'BLOCCATO'}")

    # Caso B: flapping. Apro e chiudo l'interruttore a raffica.
    # Un interruttore reale non può aprirsi/chiudersi così in fretta:
    # vediamo se il sistema mette un limite a QUESTO tipo di comando
    # in particolare, oltre al rate limiting generico sull'IP.
    print("\nCaso B: flapping dell'interruttore (apri/chiudi x6 di fila)")
    for i in range(6):
        valore = "1" if i % 2 == 0 else "0"
        r = invia({"mittente": "tester", "target": "nodo1", "azione": "TRIP_BREAKER", "valore": valore})
        print(f"  giro {i+1}: TRIP_BREAKER={valore} -> {'ACCETTATO' if accettato(r) else 'BLOCCATO'}")

    # Caso C: stesso comando ripetuto identico molte volte.
    # Verifica se il sistema nota una ripetizione sospetta (es. un
    # sensore che manda sempre lo stesso identico valore non è normale
    # per una grandezza fisica reale, che oscilla sempre un po').
    print("\nCaso C: stesso identico comando ripetuto 5 volte")
    for i in range(5):
        r = invia({"mittente": "tester", "target": "nodo1", "azione": "SET_FREQUENCY", "valore": "50.0"})
        print(f"  ripetizione {i+1}: SET_FREQUENCY=50.0 -> {'ACCETTATO' if accettato(r) else 'BLOCCATO'}")

    # Caso D: bypass del rate limiting usando ip_simulato diverso
    # per ogni richiesta, inviate senza pause. Verifica il bug già
    # trovato nel load test: il rate limit si basa sull'IP reale
    # (ip_source) solo come DEFAULT, ma se mando ip_simulato esplicito
    # e diverso a ogni colpo, lo aggiro del tutto.
    print("\nCaso D: bypass del rate limiting con ip_simulato diverso ad ogni richiesta")
    accettati = 0
    for i in range(10):
        messaggio = {
            "mittente": "tester",
            "ip_simulato": f"10.0.0.{i}",
            "target": "nodo1",
            "azione": "SET_VOLTAGE",
            "valore": "20000",
        }
        dati = (json.dumps(messaggio) + "\n").encode("utf-8")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        try:
            sock.connect((HOST, PORT))
            sock.sendall(dati)
            r = sock.recv(1024).decode("utf-8", errors="replace")
            if accettato(r):
                accettati += 1
        except OSError:
            pass
        finally:
            sock.close()
        # NOTA: qui niente time.sleep(1.1): vogliamo mandarle il più
        # vicino possibile nel tempo, proprio per testare il bypass.
    print(f"  10 richieste, IP simulati diversi, nessuna pausa -> {accettati}/10 accettate")
    print("  (se accettati è alto, il rate limiting e' aggirabile dichiarando IP diversi)")


def main():
    test_confini()
    test_sequenze()
    print("\n===== FINE EDGE-CASE LOGIC TEST =====")


if __name__ == "__main__":
    main()