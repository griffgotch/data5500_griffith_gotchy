def count_nodes(graph):
    return graph.number_of_nodes()

G = nx.Graph()
G.add_nodes_from([1, 2, 3, 4, 5])
G.add_edges_from([(1, 2), (2, 3), (3, 4)])

print('Nodes in graph:', count_nodes(G))