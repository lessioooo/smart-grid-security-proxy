import matplotlib.pyplot as plt
import networkx as nx
from digital_twin import SmartGridTwin

def visualizza_topologia(grid):
    """Genera un plot visivo pulito ed elegante del grafo"""
    plt.figure(figsize=(11, 5), facecolor='white')
    
    # Coordinate geometriche simmetriche
    posizioni = {
        "centrale": (0, 1), 
        "sottostazione_nord": (1, 2),
        "sottostazione_sud": (1, 0),
        "cabina_residenziale": (2, 2),
        "cabina_scolastica": (2, 0),cabina_commerciale, cabina_sportiva
        "Ospedale": (3, 1)
    }
    
    # Palette di colori moderna e professionale
    colori_nodi = []
    for nodo, dati in grid.nodes(data=True):
        if dati["tipo"] == "sorgente":
            colori_nodi.append("#2ecc71")  # Verde brillante
        elif dati["tipo"] == "critico":
            colori_nodi.append("#e74c3c")  # Rosso allarme
        else:
            colori_nodi.append("#3498db")  # Blu tecnico
            
    # Disegno dei componenti con stili curati
    nx.draw_networkx_nodes(
        grid, pos=posizioni, 
        node_color=colori_nodi, 
        node_size=3200, 
        edgecolors="black", 
        linewidths=1.5
    )
    
    nx.draw_networkx_edges(
        grid, pos=posizioni, 
        edge_color="#7f8c8d", 
        width=2, 
        arrows=True, 
        arrowsize=18,
        arrowstyle="-|>"
    )
    
    # Etichette con testo bianco in grassetto per massima leggibilità
    nx.draw_networkx_labels(
        grid, pos=posizioni, 
        font_size=10, 
        font_weight="bold", 
        font_color="white"
    )
    
    plt.title("Digital Twin - Smart Grid Topology", fontsize=14, fontweight="bold", pad=15)
    plt.axis("off")  # Nasconde gli assi numerici per un look pulito
    plt.tight_layout()
    
    # Salvataggio e visualizzazione
    plt.savefig("topologia_grid.png", dpi=300, bbox_inches="tight")
    print("\n[EXPORT] Immagine grafica pulita salvata come 'topologia_grid.png'.")
    plt.show()
        # Generazione e visualizzazione del grafico pulito
    visualizza_topologia(rete)

    if __name__ == "__main__":
    twin = SmartGridTwin()
    visualizza_topologia(twin.grid)