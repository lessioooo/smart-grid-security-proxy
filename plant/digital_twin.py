import networkx as nx 
import json
import socket
import threading
import os

CHIUSO = "CHIUSO"
APERTO = "APERTO"

TRIP_BREAKER = "TRIP_BREAKER"
AZIONI = {TRIP_BREAKER}
VALORI_BREAKER = {"0": CHIUSO, "1": APERTO}

HOST = "0.0.0.0"
PORTA = 5001

#Legge dalla variabile d'ambiente IP_CONSENTITI l'elenco degli IP ammessi, se la variabile non esiste, ammette solo la macchina locale ("127.0.0.1").
IP_CONSENTITI = set(os.environ.get("IP_CONSENTITI", "127.0.0.1").split(",")) 

class SmartGridTwin:
    def __init__(self):
        self.grid = nx.DiGraph()
        self.lock = threading.Lock()  # Lock per garantire thread safety durante l'accesso alla rete
        nodi = [ #Definizione dei nodi con attributi di tipo e stato
            ("centrale", {"tipo": "sorgente", "stato": CHIUSO}),
            ("sottostazione_nord", {"tipo": "transito", "stato": CHIUSO}),
            ("sottostazione_sud", {"tipo": "transito", "stato": CHIUSO}),
            ("cabina_residenziale", {"tipo": "carico", "stato": CHIUSO}),
            ("cabina_scolastica", {"tipo": "carico", "stato": CHIUSO}),
            ("cabina_commerciale", {"tipo": "carico", "stato": CHIUSO}),
            ("cabina_sportiva", {"tipo": "carico", "stato": CHIUSO}),
            ("ospedale", {"tipo": "critico", "stato": CHIUSO})
        ]

        archi = [ #Definizione dei collegamenti direzionati del grafo
            ("centrale", "sottostazione_nord"),
            ("centrale", "sottostazione_sud"),
            ("sottostazione_nord", "cabina_residenziale"),
            ("sottostazione_nord", "cabina_scolastica"),
            ("sottostazione_nord", "ospedale"),
            ("sottostazione_sud", "cabina_commerciale"),
            ("sottostazione_sud", "cabina_sportiva"),
            ("sottostazione_sud", "ospedale")
        ]

        self.grid.add_nodes_from(nodi)
        self.grid.add_edges_from(archi)

    def stato_nodi(self):
        return {nome: attributi["stato"] for nome, attributi in self.grid.nodes(data=True)}

    def ospedale_alimentato(self): #Verifica se esiste un percorso dalla centrale all'ospedale considerando solo i nodi chiusi
        nodi_chiusi = [nome for nome, attributi in self.grid.nodes(data=True) if attributi["stato"] == CHIUSO]
        sottografo = self.grid.subgraph(nodi_chiusi) #Definizione del sottografo contenente solo i nodi chiusi
        try:
            return nx.has_path(sottografo, "centrale", "ospedale")
        except nx.NodeNotFound: #se l'ospedale o la centrale sono isolati, non sono presenti nel sottografo, quindi è normale che nonn esista un percorso che colleghi centrale e ospedale
            return False

    def esegui_comando(self, cmd):
        target = cmd.get("target")
        azione = cmd.get("azione")
        valore = cmd.get("valore")
        if not isinstance(target, str) or not isinstance(azione, str) or not isinstance(valore, str):
            return {"status": "ERROR", "codice_errore": "CAMPO_MANCANTE"}
        if azione not in AZIONI:
            return {"status": "ERROR", "codice_errore": "AZIONE_SCONOSCIUTA"}
        if valore not in VALORI_BREAKER:
            return {"status": "ERROR", "codice_errore": "VALORE_NON_VALIDO"}
        if target not in self.grid.nodes:
            return {"status": "ERROR", "codice_errore": "NODO_INESISTENTE"}
        with self.lock:  # Acquisizione del lock per garantire thread safety: garantisce che un solo thread alla volta possa modificare lo stato dei nodi
            self.grid.nodes[target]["stato"] = VALORI_BREAKER[valore]
            return {"status": "SUCCESS", "ospedale_alimentato": self.ospedale_alimentato(), "stato_nodi": self.stato_nodi()}
    
    def processa_json(self, testo):
        try:
            cmd = json.loads(testo) #Decodifica la stringa json in un dizionario python
        except (json.JSONDecodeError, TypeError, RecursionError):
            return {"status": "ERROR", "codice_errore": "JSON_NON_VALIDO"}
        if not isinstance(cmd, dict):
            return {"status": "ERROR", "codice_errore": "JSON_NON_VALIDO"}
        return self.esegui_comando(cmd)  

def gestisci_client(conn, addr, twin):
    with conn: 
        conn.settimeout(5.0)  #Se per 5 secondi sulla connessione stabilita non succede niente solleva eccezione
        try:
            dati = conn.recv(4096) #Può ricevere un massimo di 4096 byte
            testo = dati.decode("utf-8", errors="replace") #Decodifica byte -> stringa; i byte illeggibili vengono sostituiti con carattere di sostituzione
            risposta = twin.processa_json(testo) #Controlla che la stringa sia un json valido; restituisce sempre un dizionario python
        except socket.timeout:
            risposta = {"status": "ERROR", "codice_errore": "TIMEOUT"}
        except OSError: #Cattura errori di connessione, ad esempio se il client chiude la connessione prima che il server abbia finito di leggere i dati
            return
        try:
            conn.sendall(json.dumps(risposta).encode("utf-8")) #Codifica inversa: dizionario -> testo json -> byte; sendall invia tutti i byte al client
        except OSError:
            pass  # Se la connessione è stata chiusa dal client, ignora l'errore

def avvia_server():
    twin = SmartGridTwin()
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #Questa riga crea un socket che funziona su reti ipV4 (AF_INET) tramite il protocollo TCP (SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) #Permette di riavviare il server subito dopo averlo fermato
    server.bind((HOST, PORTA)) #Assegna al socket host e porta (5001)
    server.listen() #Da qui il server si mette in ascolto di connessioni in arrivo e le mette in coda
    print("Sportello aperto sulla porta", PORTA)
    while True: #Server continua all'infinito 
        conn, addr = server.accept() #accept() blocca l'esecuzione finché non arriva una connessione; quando arriva, restituisce un nuovo socket (conn) e l'indirizzo del client (addr)
        print("Connessione da", addr)
        if addr[0] not in IP_CONSENTITI: #Se l'IP del client non è nella lista degli IP consentiti, chiude la connessione
            print("Connessione rifiutata da", addr)
            conn.close()
            continue
        thread = threading.Thread(      #Crea un nuovo thread, un ramo che permette di gestire la connessione con il client, in parallelo ad altre connessioni; in questo modo il server può gestire più client contemporaneamente
            target = gestisci_client, 
            args = (conn, addr, twin),
            daemon = True  # Thread demone: si chiude automaticamente quando il programma principale termina
        )
        thread.start() #Fa partire il thread

if __name__ == "__main__":
   avvia_server()