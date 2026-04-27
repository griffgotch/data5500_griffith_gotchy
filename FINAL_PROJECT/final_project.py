import os
import csv
import json
import math
import requests
import networkx as nx
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

#ALPACA KEY
from dotenv import load_dotenv

load_dotenv()  # loads variables from .env into os.environ 

ALPACA_API_KEY    = os.environ.get("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.environ.get("ALPACA_SECRET_KEY")

# Add a guard so the script fails loudly if keys are missing
if not ALPACA_API_KEY or not ALPACA_SECRET_KEY:
    raise EnvironmentError(
        "Missing Alpaca credentials. "
        "Set ALPACA_API_KEY and ALPACA_SECRET_KEY in your .env file."
    )

TRADE_NOTIONAL_USD = 100.0

MIN_DEVIATION_TO_TRADE = 0.005

DATA_DIR = "data"


COIN_IDS = {
    "bitcoin":        "BTC",
    "ethereum":       "ETH",
    "litecoin":       "LTC",
    "ripple":         "XRP",
    "cardano":        "ADA",
    "bitcoin-cash":   "BCH",
    "eos":            "EOS",
    "solana":         "SOL",
    "dogecoin":       "DOGE",
    "polkadot":       "DOT",
    "chainlink":      "LINK",
}

ALPACA_TRADABLE = {"BTC", "ETH", "LTC", "BCH", "SOL", "DOGE", "LINK", "DOT"}

COINGECKO_IDS    = ",".join(COIN_IDS.keys())
COINGECKO_CURRENCIES = ",".join(t.lower() for t in COIN_IDS.values())

COINGECKO_URL = (
    f"https://api.coingecko.com/api/v3/simple/price"
    f"?ids={COINGECKO_IDS}"
    f"&vs_currencies={COINGECKO_CURRENCIES}"
)

# 1. Data Fetching

def fetch_exchange_rates():
    print("Fetching live exchange rates from CoinGecko...")
    response = requests.get(COINGECKO_URL, timeout=15)
    response.raise_for_status()
    data = response.json()
    print(f"  Received data for {len(data)} coins.\n")
    return data

# 2. CSV

def save_to_csv(exchange_rates):
    os.makedirs(DATA_DIR, exist_ok=True)

    et = ZoneInfo("America/New_York")
    now = datetime.now(tz=et)
    filename = now.strftime("currency_pair_%Y.%m.%d:%H.%M.txt")
    filepath = os.path.join(DATA_DIR, filename)

    rows_written = 0
    with open(filepath, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["currency_from", "currency_to", "exchange_rate"])

        for coin_id, rates in exchange_rates.items():
            from_ticker = COIN_IDS[coin_id].upper()
            for to_ticker_lower, rate in rates.items():
                to_ticker = to_ticker_lower.upper()
                if from_ticker != to_ticker:
                    writer.writerow([from_ticker, to_ticker, rate])
                    rows_written += 1

    print(f"  Saved {rows_written} currency pairs → {filepath}\n")
    return filepath


# 3. Graph

def build_graph(exchange_rates):
    graph = nx.DiGraph()

    for coin_id, rates in exchange_rates.items():
        from_ticker = COIN_IDS[coin_id].upper()
        for to_ticker_lower, rate in rates.items():
            to_ticker = to_ticker_lower.upper()
            if from_ticker != to_ticker and rate and rate > 0:
                graph.add_edge(from_ticker, to_ticker, weight=rate)

    print(f"  Graph built: {graph.number_of_nodes()} nodes, "
          f"{graph.number_of_edges()} edges\n")
    return graph


# 4. Path Weight

def calculate_path_weight(graph, path):
    weight = 1.0
    for i in range(len(path) - 1):
        weight *= graph[path[i]][path[i + 1]]["weight"]
    return weight

# 5. Arbitrage Detection

def find_arbitrage_opportunities(graph):
    nodes = list(graph.nodes)
    min_record = None
    max_record = None
    disequilibrium_list = []

    print("Searching...\n")
    print("-" * 70)

    for source in nodes:
        for target in nodes:
            if source == target:
                continue

            try:
                forward_paths = list(nx.all_simple_paths(graph, source, target, cutoff=4))
                reverse_paths = list(nx.all_simple_paths(graph, target, source, cutoff=4))
            except nx.NetworkXError:
                continue

            if not forward_paths or not reverse_paths:
                continue

            best_forward = max(forward_paths,
                               key=lambda p: calculate_path_weight(graph, p))
            best_forward_weight = calculate_path_weight(graph, best_forward)

            best_reverse = max(reverse_paths,
                               key=lambda p: calculate_path_weight(graph, p))
            best_reverse_weight = calculate_path_weight(graph, best_reverse)

            factor = best_forward_weight * best_reverse_weight
            deviation = factor - 1.0

            record = {
                "path_forward":   best_forward,
                "path_reverse":   best_reverse,
                "weight_forward": best_forward_weight,
                "weight_reverse": best_reverse_weight,
                "factor":         factor,
            }

            print(f"  Forward : {' -> '.join(best_forward):<50}  "
                  f"weight = {best_forward_weight:.8f}")
            print(f"  Reverse : {' -> '.join(best_reverse):<50}  "
                  f"weight = {best_reverse_weight:.8f}")
            print(f"  Factor  : {factor:.10f}")

            if abs(deviation) > 0.0001:
                print(f"  *** DIS-EQUILIBRIUM DETECTED  (deviation: {deviation:+.6f}) ***")
                disequilibrium_list.append(record)
            print()

            if min_record is None or factor < min_record["factor"]:
                min_record = record
            if max_record is None or factor > max_record["factor"]:
                max_record = record

    return min_record, max_record, disequilibrium_list


# 6. Paper Trading via Alpaca

def get_alpaca_client():
    return TradingClient(
        api_key=ALPACA_API_KEY,
        secret_key=ALPACA_SECRET_KEY,
        paper=True
    )


def ticker_to_alpaca_symbol(ticker: str) -> str | None:
    if ticker in ALPACA_TRADABLE:
        return f"{ticker}/USD"
    return None


def place_paper_trade(client, symbol: str, side: OrderSide, notional: float):
    try:
        order_data = MarketOrderRequest(
            symbol=symbol,
            notional=round(notional, 2),
            side=side,
            time_in_force=TimeInForce.IOC,
        )
        order = client.submit_order(order_data)
        print(f"   Order submitted: {side.value.upper()} ${notional:.2f} of {symbol} "
              f"  [order_id: {order.id}]")
        return order
    except Exception as exc:
        print(f"   Order FAILED for {symbol} ({side.value}): {exc}")
        return None


def execute_arbitrage_trades(disequilibrium_list):
    if not disequilibrium_list:
        print("  No dis-equilibrium opportunities meet the trade threshold.\n")
        return

    print("\n" + "-" * 70)
    print("PAPER TRADING — Executing arbitrage orders in Alpaca")
    print("-" * 70 + "\n")

    try:
        client = get_alpaca_client()
        account = client.get_account()
        print(f"  Alpaca paper account equity : ${float(account.equity):,.2f}")
        print(f"  Buying power               : ${float(account.buying_power):,.2f}\n")
    except Exception as exc:
        print(f"  Could not connect to Alpaca: {exc}")
        print("  Skipping paper trades.\n")
        return

    trades_placed = 0

    for record in disequilibrium_list:
        deviation = record["factor"] - 1.0
        if abs(deviation) < MIN_DEVIATION_TO_TRADE:
            continue

        if deviation > 0:
            path  = record["path_forward"]
            label = "factor > 1 → trading forward path"
        else:
            path  = record["path_reverse"]
            label = "factor < 1 → trading reverse path"

        print(f"  Opportunity: {' -> '.join(path)}  "
              f"(factor={record['factor']:.8f}, deviation={deviation:+.6f})")
        print(f"  Strategy: {label}")

        for i in range(len(path) - 1):
            sell_ticker = path[i]
            buy_ticker  = path[i + 1]

            sell_symbol = ticker_to_alpaca_symbol(sell_ticker)
            buy_symbol  = ticker_to_alpaca_symbol(buy_ticker)

            if sell_symbol:
                place_paper_trade(client, sell_symbol, OrderSide.SELL, TRADE_NOTIONAL_USD)
                trades_placed += 1
            else:
                print(f"  Skipping SELL {sell_ticker} — not tradable on Alpaca")

            if buy_symbol:
                place_paper_trade(client, buy_symbol, OrderSide.BUY, TRADE_NOTIONAL_USD)
                trades_placed += 1
            else:
                print(f"  Skipping BUY {buy_ticker} — not tradable on Alpaca")

        print()

    print(f"  Total paper orders placed this run: {trades_placed}\n")


# 7. Save Results

def save_results(min_record, max_record, disequilibrium_list):
    results = {
        "run_timestamp": datetime.now(tz=ZoneInfo("America/New_York")).strftime("%Y-%m-%d %H:%M:%S ET"),
        "total_disequilibrium_found": len(disequilibrium_list),
        "lowest_factor": {
            "path_forward":   " -> ".join(min_record["path_forward"]),
            "path_reverse":   " -> ".join(min_record["path_reverse"]),
            "weight_forward": min_record["weight_forward"],
            "weight_reverse": min_record["weight_reverse"],
            "factor":         min_record["factor"],
        },
        "highest_factor": {
            "path_forward":   " -> ".join(max_record["path_forward"]),
            "path_reverse":   " -> ".join(max_record["path_reverse"]),
            "weight_forward": max_record["weight_forward"],
            "weight_reverse": max_record["weight_reverse"],
            "factor":         max_record["factor"],
        },
        "all_opportunities": [
            {
                "path_forward":   " -> ".join(r["path_forward"]),
                "path_reverse":   " -> ".join(r["path_reverse"]),
                "weight_forward": r["weight_forward"],
                "weight_reverse": r["weight_reverse"],
                "factor":         r["factor"],
                "deviation":      r["factor"] - 1.0,
            }
            for r in disequilibrium_list
        ]
    }

    output_dir = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(output_dir, "results.json")

    with open(filepath, "w") as f:
        json.dump(results, f, indent=2)

    print(f"  Results saved → {filepath}\n")

# 8. Summary

def print_summary(min_record, max_record):
    print("-" * 70)
    print("SUMMARY: EXTREME ARBITRAGE OPPORTUNITIES")
    print("-" * 70)

    print("\n  [LOWEST FACTOR — Least favorable round-trip]")
    print(f"  Forward : {' -> '.join(min_record['path_forward'])}")
    print(f"  Reverse : {' -> '.join(min_record['path_reverse'])}")
    print(f"  Factor  : {min_record['factor']:.10f}")

    print("\n  [HIGHEST FACTOR — Best arbitrage opportunity]")
    print(f"  Forward : {' -> '.join(max_record['path_forward'])}")
    print(f"  Reverse : {' -> '.join(max_record['path_reverse'])}")
    print(f"  Factor  : {max_record['factor']:.10f}")
    print("-" * 70 + "\n")


# 9. Main

def main():
    et = ZoneInfo("America/New_York")
    run_time = datetime.now(tz=et).strftime("%Y-%m-%d %H:%M:%S ET")
    print("=" * 70)
    print(f"  Crypto Arbitrage Detector  |  {run_time}")
    print("=" * 70 + "\n")

    exchange_rates = fetch_exchange_rates()

    print("Saving currency pair data...")
    save_to_csv(exchange_rates)

    print("Building exchange-rate graph...")
    graph = build_graph(exchange_rates)

    min_record, max_record, disequilibrium_list = find_arbitrage_opportunities(graph)

    execute_arbitrage_trades(disequilibrium_list)

    #Print summary
    if min_record and max_record:
        print_summary(min_record, max_record)

    if min_record and max_record:
        save_results(min_record, max_record, disequilibrium_list)

    print("Run complete.\n")


if __name__ == "__main__":
    main()