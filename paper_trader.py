import ccxt
import time
import csv

# =================================================================
# TRADING BOT KONFIGURATION (PAPER TRADING)
# =================================================================
EXCHANGE_NAME = "bitrue"
TRADE_AMOUNT_USDT = 10.0      # Einsatz: 10 USDT / EUR
MIN_PROFIT_THRESHOLD = 0.01  # Mindestgewinn in %
TAKER_FEE = 0.002            # 0.2% Bitrue Fee
TOTAL_SCANS = 10             # Anzahl der Scans pro Workflow-Durchlauf

TRIANGLE_ROUTES = [
    ["USDT", "DFI", "BTC", "USDT"],
    ["USDT", "DFI", "ETH", "USDT"],
    ["USDT", "ETH", "BTC", "USDT"],
    ["USDT", "XRP", "BTC", "USDT"],
    ["USDT", "LTC", "BTC", "USDT"],
]

exchange = getattr(ccxt, EXCHANGE_NAME)({'enableRateLimit': True})

def fetch_ticker(symbol):
    try:
        return exchange.fetch_ticker(symbol)
    except Exception:
        return None

def evaluate_route(route, amount):
    a, b, c, _ = route
    ticker1 = fetch_ticker(f"{b}/{a}")
    ticker2 = fetch_ticker(f"{b}/{c}")
    ticker3 = fetch_ticker(f"{c}/{a}")
    
    if not (ticker1 and ticker2 and ticker3):
        return None
    
    rate1 = 1 / ticker1['ask']
    amount_b = amount * rate1 * (1 - TAKER_FEE)
    
    rate2 = ticker2['bid']
    amount_c = amount_b * rate2 * (1 - TAKER_FEE)
    
    rate3 = ticker3['bid']
    final_a = amount_c * rate3 * (1 - TAKER_FEE)
    
    profit_pct = ((final_a - amount) / amount) * 100
    profit_usd = final_a - amount
    return profit_pct, profit_usd

def run():
    results = []
    print(f"🔎 Starte {TOTAL_SCANS} Dreiecks-Arbitrage-Scans auf BITRUE...")
    
    for scan in range(1, TOTAL_SCANS + 1):
        print(f"\n--- Scan {scan}/{TOTAL_SCANS} ---")
        for route in TRIANGLE_ROUTES:
            res = evaluate_route(route, TRADE_AMOUNT_USDT)
            if res:
                pct, usd = res
                route_str = " -> ".join(route)
                print(f"🔄 Pfad: {route_str:<32} | Netto: {pct:+.4f}%")
                
                results.append({
                    "scan": scan,
                    "route": route_str,
                    "profit_pct": round(pct, 4),
                    "profit_usd": round(usd, 4),
                    "accepted": pct >= MIN_PROFIT_THRESHOLD
                })
            time.sleep(0.2)
            
    # Ergebnisse in CSV-Datei schreiben
    with open("trading_results.csv", mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["scan", "route", "profit_pct", "profit_usd", "accepted"])
        writer.writeheader()
        writer.writerows(results)
        
    print("\n✅ Analyse abgeschlossen. Ergebnisse in 'trading_results.csv' gespeichert.")

if __name__ == "__main__":
    run()
