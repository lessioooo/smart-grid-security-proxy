import networkx as nx 

CHIUSO = "CHIUSO"
APERTO = "APERTO"
CHIUDI = "CHIUDI"
APRI = "APRI"
AZIONI = {APRI : APERTO, CHIUDI : CHIUSO}

class SmartGridTwin:
    def __init__(self):
        self.grid = nx.DiGraph()
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
        nodo = cmd.get("nodo")
        azione = cmd.get("azione")
        if not isinstance(nodo, str) or not isinstance(azione, str):
            return {"status": "ERROR", "codice_errore": "CAMPO_MANCANTE"}
        if azione not in AZIONI:
            return {"status": "ERROR", "codice_errore": "AZIONE_SCONOSCIUTA"}
        if nodo not in self.grid.nodes:
            return {"status": "ERROR", "codice_errore": "NODO_INESISTENTE"}
        self.grid.nodes[nodo]["stato"] = AZIONI[azione]
        return {"status": "SUCCESS", "ospedale_alimentato": self.ospedale_alimentato(), "stato_nodi": self.stato_nodi()}

if __name__ == "__main__":
    twin = SmartGridTwin()
    print("Stato iniziale dei nodi:", twin.stato_nodi())
    print("Sono presenti", twin.grid.number_of_nodes(), "nodi e", twin.grid.number_of_edges(), "archi nella rete.")

    print(twin.esegui_comando({"nodo": "sottostazione_nord", "azione": "APRI"}))
    print(twin.esegui_comando({"nodo": "sottostazione_sud", "azione": "APRI"}))
    print(twin.esegui_comando({"nodo": "sottostazione_sud", "azione": "CHIUDI"}))
    print(twin.esegui_comando({"nodo": "ospedale"}))
    print(twin.esegui_comando({"nodo": "ospedale", "azione": "PIPPO"}))
    print(twin.esegui_comando({"nodo": "pippo", "azione": "APRI"}))