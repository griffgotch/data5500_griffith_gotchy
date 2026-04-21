import networkx as nx

def count_high_degree_nodes(graph):
    return sum(1 for _, degree in graph.degree() if degree > 5)

G = nx.barabasi_albert_graph(100, 6)

result = count_high_degree_nodes(G)
print(f"Nodes with degree > 5: {result}")