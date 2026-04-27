import requests
import networkx as nx
 
#CoinGecko coin IDs and ticker symbols
COIN_IDS = {
    "bitcoin":      "btc",
    "ethereum":     "eth",
    "litecoin":     "ltc",
    "ripple":       "xrp",
    "cardano":      "ada",
    "bitcoin-cash": "bch",
    "eos":          "eos",
}
 
COINGECKO_URL = (
    "https://api.coingecko.com/api/v3/simple/price"
    "?ids=ethereum,bitcoin,litecoin,ripple,cardano,bitcoin-cash,eos"
    "&vs_currencies=eth,btc,ltc,xrp,ada,bch,eos"
)
 
#Data Fetching
 
def fetch_exchange_rates():
    print("Fetching live exchange rates from CoinGecko...")
    response = requests.get(COINGECKO_URL)
    response.raise_for_status()
    return response.json()
 
 
#Graph Construction
 
def build_graph(exchange_rates):
    graph = nx.DiGraph()
 
    for coin_id, rates in exchange_rates.items():
        from_ticker = COIN_IDS[coin_id]
        for to_ticker, rate in rates.items():
            # Skip self-loops (e.g. btc -> btc = 1.0)
            if from_ticker != to_ticker:
                graph.add_edge(from_ticker, to_ticker, weight=rate)
 
    print(f"{graph.number_of_nodes()} "
          f" {graph.number_of_edges()}\n")
    return graph
 
 
# Path Weight Calculation
 
def calculate_path_weight(graph, path):
    weight = 1.0
    for i in range(len(path) - 1):
        weight *= graph[path[i]][path[i + 1]]['weight']
    return weight

 
def find_arbitrage_opportunities(graph):
    nodes = list(graph.nodes)
 
    min_record = None
    max_record = None
 
    for source in nodes:
        for target in nodes:
            if source == target:
                continue
 
          
            forward_paths = list(nx.all_simple_paths(graph, source, target))
            if not forward_paths:
                continue
 
            reverse_paths = list(nx.all_simple_paths(graph, target, source))
            if not reverse_paths:
                continue
 
            best_forward = max(
                forward_paths,
                key=lambda p: calculate_path_weight(graph, p)
            )
            best_forward_weight = calculate_path_weight(graph, best_forward)
 
            # Find the best (highest weight) reverse path
            best_reverse = max(
                reverse_paths,
                key=lambda p: calculate_path_weight(graph, p)
            )
            best_reverse_weight = calculate_path_weight(graph, best_reverse)
 
            factor = best_forward_weight * best_reverse_weight
 
            record = {
                "path_forward":    best_forward,
                "path_reverse":    best_reverse,
                "weight_forward":  best_forward_weight,
                "weight_reverse":  best_reverse_weight,
                "factor":          factor,
            }
 
            # Print every result
            print(f"  Forward : {' -> '.join(best_forward):<40}  "
                  f"weight = {best_forward_weight:.8f}")
            print(f"  Reverse : {' -> '.join(best_reverse):<40}  "
                  f"weight = {best_reverse_weight:.8f}")
            print(f"  Factor  : {factor:.10f}")
            if abs(factor - 1.0) > 0.0001:
                print(f"  *** DIS-EQUILIBRIUM DETECTED (factor deviation: "
                      f"{factor - 1.0:+.6f}) ***")
            print()
 
            # Track min and max
            if min_record is None or factor < min_record["factor"]:
                min_record = record
            if max_record is None or factor > max_record["factor"]:
                max_record = record
 
    return min_record, max_record
 
 
def print_summary(min_record, max_record):
    print("-" * 65)
    print("SUMMARY: EXTREME ARBITRAGE OPPORTUNITIES")
    print("-" * 65)
 
    print("\n  [LOWEST FACTOR - Least favorable trade]")
    print(f"  Forward : {' -> '.join(min_record['path_forward'])}")
    print(f"  Reverse : {' -> '.join(min_record['path_reverse'])}")
    print(f"  Factor  : {min_record['factor']:.10f}")
 
    print("\n  [HIGHEST FACTOR - Best arbitrage opportunity]")
    print(f"  Forward : {' -> '.join(max_record['path_forward'])}")
    print(f"  Reverse : {' -> '.join(max_record['path_reverse'])}")
    print(f"  Factor  : {max_record['factor']:.10f}")
    print("-" * 65)

 
# --- Main ---
 
def main():
    # 1. Fetch live data
    exchange_rates = fetch_exchange_rates()
 
    # 2. Build the graph
    graph = build_graph(exchange_rates)
 
    # 3. Search all paths for arbitrage
    print("Searching all currency paths for dis-equilibrium...\n")
    print("-" * 65)
    min_record, max_record = find_arbitrage_opportunities(graph)
 
    # 4. Print summary
    print_summary(min_record, max_record)
 
 
if __name__ == "__main__":
    main()