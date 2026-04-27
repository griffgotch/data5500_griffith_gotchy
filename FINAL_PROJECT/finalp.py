import os
import csv
import math
import requests
import networkx as nx
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

#ALPACA KEY
ALPACA_API_KEY    = os.environ.get("PKMA6OFSAT556BKL2G2U7X2KF4")
ALPACA_SECRET_KEY = os.environ.get("91Yurv8AsT4gu5Lta3HZxJo6z54xikoBVkNeFwsjPp8L")

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
    "avalanche-2":    "AVAX",
    "stellar":        "XLM",
}

# Alpaca supports these crypto symbols for trading (symbol format: "BTC/USD")
# Only these can be paper-traded via Alpaca
ALPACA_TRADABLE = {"BTC", "ETH", "LTC", "BCH", "SOL", "DOGE", "AVAX", "LINK", "XLM", "DOT"}

COINGECKO_IDS    = ",".join(COIN_IDS.keys())
COINGECKO_CURRENCIES = ",".join(t.lower() for t in COIN_IDS.values())

COINGECKO_URL = (
    f"https://api.coingecko.com/api/v3/simple/price"
    f"?ids={COINGECKO_IDS}"
    f"&vs_currencies={COINGECKO_CURRENCIES}"
)


# ---------------------------------------------------------------------------
# 1. Data Fetching
# ---------------------------------------------------------------------------

def fetch_exchange_rates():
    print("Fetching live exchange rates from CoinGecko...")
    response = requests.get(COINGECKO_URL, timeout=15)
    response.raise_for_status()
    data = response.json()
    print(f"  Received data for {len(data)} coins.\n")
    return data


# ---------------------------------------------------------------------------
# 2. CSV Persistence  →  data/currency_pair_YYYY.MM.DD:HH.MM.txt
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# 3. Graph Construction
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# 4. Path Weight
# ---------------------------------------------------------------------------

def calculate_path_weight(graph, path):
    weight = 1.0
    for i in range(len(path) - 1):
        weight *= graph[path[i]][path[i + 1]]["weight"]
    return weight


# ---------------------------------------------------------------------------
# 5. Arbitrage Detection
# ---------------------------------------------------------------------------

def find_arbitrage_opportunities(graph):
    """
    For every ordered (source, target) pair find the best forward and reverse
    path. Report pairs where the round-trip factor deviates from 1.0.

    Returns the min-factor and max-factor records.
    """
    nodes = list(graph.nodes)
    min_record = None
    max_record = None
    disequilibrium_list = []

    print("Searching all currency paths for dis-equilibrium...\n")
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


# ---------------------------------------------------------------------------
# 6. Paper Trading via Alpaca
# ---------------------------------------------------------------------------

def get_alpaca_client():
    """Return an Alpaca paper-trading client."""
    return TradingClient(
        api_key=ALPACA_API_KEY,
        secret_key=ALPACA_SECRET_KEY,
        paper=True          # ← paper trading, never real money
    )


def ticker_to_alpaca_symbol(ticker: str) -> str | None:
    """Convert e.g. 'BTC' → 'BTC/USD'.  Returns None if not tradable on Alpaca."""
    if ticker in ALPACA_TRADABLE:
        return f"{ticker}/USD"
    return None


def place_paper_trade(client, symbol: str, side: OrderSide, notional: float):
    """
    Place a notional market order on Alpaca paper trading.
    `symbol`   : e.g. 'BTC/USD'
    `side`     : OrderSide.BUY or OrderSide.SELL
    `notional` : USD amount
    """
    try:
        order_data = MarketOrderRequest(
            symbol=symbol,
            notional=round(notional, 2),
            side=side,
            time_in_force=TimeInForce.IOC,  # Immediate-or-cancel for crypto
        )
        order = client.submit_order(order_data)
        print(f"    ✓ Order submitted: {side.value.upper()} ${notional:.2f} of {symbol} "
              f"  [order_id: {order.id}]")
        return order
    except Exception as exc:
        print(f"    ✗ Order FAILED for {symbol} ({side.value}): {exc}")
        return None


def execute_arbitrage_trades(disequilibrium_list):
    """
    For each dis-equilibrium record whose factor deviates enough, walk the
    forward path buying each leg, then walk the reverse path to close.
    Only coins supported by Alpaca are traded.
    """
    if not disequilibrium_list:
        print("  No dis-equilibrium opportunities meet the trade threshold.\n")
        return

    print("\n" + "=" * 70)
    print("PAPER TRADING — Executing arbitrage orders via Alpaca")
    print("=" * 70 + "\n")

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

        forward_path = record["path_forward"]
        reverse_path = record["path_reverse"]

        print(f"  Opportunity: {' -> '.join(forward_path)}  "
              f"(factor={record['factor']:.8f}, deviation={deviation:+.6f})")

        # Determine trade direction based on factor
        # factor > 1 → forward path is profitable (buy forward, sell reverse)
        # factor < 1 → reverse path is profitable (buy reverse, sell forward)
        if deviation > 0:
            buy_path  = forward_path
            sell_path = reverse_path
            label     = "factor > 1 → buy forward leg"
        else:
            buy_path  = reverse_path
            sell_path = forward_path
            label     = "factor < 1 → buy reverse leg"

        print(f"  Strategy: {label}")

        # Place BUY orders along the profitable path
        for ticker in buy_path:
            symbol = ticker_to_alpaca_symbol(ticker)
            if symbol:
                place_paper_trade(client, symbol, OrderSide.BUY, TRADE_NOTIONAL_USD)
                trades_placed += 1

        # Place SELL orders along the closing path
        for ticker in sell_path:
            symbol = ticker_to_alpaca_symbol(ticker)
            if symbol:
                place_paper_trade(client, symbol, OrderSide.SELL, TRADE_NOTIONAL_USD)
                trades_placed += 1

        print()

    print(f"  Total paper orders placed this run: {trades_placed}\n")


# ---------------------------------------------------------------------------
# 7. Summary
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# 8. Main
# ---------------------------------------------------------------------------

def main():
    et = ZoneInfo("America/New_York")
    run_time = datetime.now(tz=et).strftime("%Y-%m-%d %H:%M:%S ET")
    print("=" * 70)
    print(f"  Crypto Arbitrage Detector  |  {run_time}")
    print("=" * 70 + "\n")

    # Step 1 — Fetch prices
    exchange_rates = fetch_exchange_rates()

    # Step 2 — Save CSV
    print("Saving currency pair data...")
    save_to_csv(exchange_rates)

    # Step 3 — Build graph
    print("Building exchange-rate graph...")
    graph = build_graph(exchange_rates)

    # Step 4 — Detect arbitrage
    min_record, max_record, disequilibrium_list = find_arbitrage_opportunities(graph)

    # Step 5 — Paper trade any dis-equilibrium cycles
    execute_arbitrage_trades(disequilibrium_list)

    # Step 6 — Print summary
    if min_record and max_record:
        print_summary(min_record, max_record)

    print("Run complete.\n")


if __name__ == "__main__":
    main()