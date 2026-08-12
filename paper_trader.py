import os
import ccxt
import time
import csv

class PaperTrader:
    def __init__(self, exchange_name="bitrue", amount=10.0, threshold=0.01, scans=50):
        self.exchange_name = exchange_name
        self.trade_amount_usdt = amount
        self.min_profit_threshold = threshold
        self.taker_fee = 0.002
        self.total_scans = scans
        
        self.exchange = getattr(ccxt, exchange_name)({'enableRateLimit': True})
        
        self.routes = [
            ["USDT", "DFI", "BTC", "USDT"],
            ["USDT", "DFI", "ETH", "USDT"],
            ["USDT", "ETH", "BTC", "USDT"],
            ["USDT", "XRP", "BTC", "USDT"],
            ["USDT", "LTC", "BTC", "USDT"],
        ]
        
        # CSV-Datei zu Beginn neu anlegen und Header schreiben
        with open("trading_results.csv", mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["scan", "route", "profit_pct", "profit_usd", "accepted"])
            writer.writeheader()

    def fetch_ticker(self, symbol):
        try:
            return self.exchange.fetch_ticker(symbol)
        except Exception:
            return None

    def evaluate_route(self, route, amount):
        a, b, c, _ = route
        ticker1 = self.fetch_ticker(f"{b}/{a}")
        ticker2 = self.fetch_ticker(f"{b}/{c}")
        ticker3 = self.fetch_ticker(f"{c}/{a}")
        
        if not (ticker1 and ticker2 and ticker3):
            return None
        
        rate1 = 1 / ticker1['ask']
        amount_b = amount * rate1 * (1 - self.taker_fee)
        
        rate2 = ticker2['bid']
        amount_c = amount_b * rate2 * (1 - self.taker_fee)
        
        rate3 = ticker3['bid']
        final_a = amount_c * rate3 * (1 - self.taker_fee)
        
        profit_pct = ((final_a - amount) / amount) * 100
        profit_usd = final_a - amount
        return profit_pct, profit_usd

    def save_result_to_csv(self, result_dict):
        # Schreibt das Ergebnis sofort fortlaufend in die Datei
        with open("trading_results.csv", mode="a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["scan", "route", "profit_pct", "profit_usd", "accepted"])
            writer.writerow(result_dict)

    def run(self):
        print(f"🔎 Starte {self.total_scans} Scans auf {self.exchange_name.upper()}...")
        
        for scan in range(1, self.total_scans + 1):
            # Zeigt den Fortschritt zur besseren Übersicht im Log
            if scan % 10 == 0 or scan == 1:
                print(f"⚡ Scan-Fortschritt: {scan}/{self.total_scans}")
                
            for route in self.routes:
                res = self.evaluate_route(route, self.trade_amount_usdt)
                if res:
                    pct, usd = res
                    route_str = " -> ".join(route)
                    accepted = pct >= self.min_profit_threshold
                    
                    # Ergebnis sofort in der CSV sichern
                    self.save_result_to_csv({
                        "scan": scan,
                        "route": route_str,
                        "profit_pct": round(pct, 4),
                        "profit_usd": round(usd, 4),
                        "accepted": accepted
                    })
                time.sleep(0.2)
                
        print("\n✅ Analyse abgeschlossen. Ergebnisse in 'trading_results.csv' gespeichert.")
