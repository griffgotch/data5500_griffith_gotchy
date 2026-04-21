import networkx as nx

def count_nodes(graph):
    return graph.number_of_nodes()

G = nx.karate_club_graph()
print(count_nodes(G)) 