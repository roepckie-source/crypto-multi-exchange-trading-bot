import csv
import time
import ccxt

class PaperTrader:
    def __init__(self, exchange_name="mexc", amount=10.0, threshold=0.01, scans=50):
        self.exchange_name = exchange_name
        self.trade_amount_usdt = amount
        self.min_profit_threshold = threshold
        self.total_scans = scans
        self.csv_file = "trading_results.csv"
        
        # MEXC Taker-Fee liegt bei 0.05% (0.0005). Bei Binance/OKX entsprechend anpassen.
        self.taker_fee = 0.0005 if exchange_name.lower() == "mexc" else 0.001
        
        self.exchange = getattr(ccxt, exchange_name)({'enableRateLimit': True})
        
        # Dreiecks-Routen: [Start/Ziel, Coin1, Coin2, Start/Ziel]
        self.routes = [
            ["USDT", "DFI", "BTC", "USDT"],
            ["USDT", "DFI", "ETH", "USDT"],
            ["USDT", "ETH", "BTC", "USDT"],
            ["USDT", "XRP", "BTC", "USDT"],
            ["USDT", "LTC", "BTC", "USDT"],
        ]
        
        # CSV-Datei neu anlegen und Header schreiben
        with open(self.csv_file, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["scan", "route", "profit_pct", "profit_usd", "accepted"])
            writer.writeheader()

    def evaluate_route_from_tickers(self, route, amount, tickers):
        """Berechnet die Arbitrage im Arbeitsspeicher aus den gesammelten Tickern."""
        a, b, c, _ = route
        
        symbol1 = f"{b}/{a}"
        symbol2 = f"{b}/{c}"
        symbol3 = f"{c}/{a}"
        
        # Prüfen, ob alle benötigten Handelspaare im Ticker-Snapshot vorhanden sind
        if not (symbol1 in tickers and symbol2 in tickers and symbol3 in tickers):
            return None
            
        t1, t2, t3 = tickers[symbol1], tickers[symbol2], tickers[symbol3]
        
        if not (t1.get('ask') and t2.get('bid') and t3.get('bid')):
            return None

        # Schritt 1: USDT -> Coin B (Kauf zum Ask-Preis)
        amount_b = (amount / t1['ask']) * (1 - self.taker_fee)
        
        # Schritt 2: Coin B -> Coin C (Verkauf zum Bid-Preis)
        amount_c = (amount_b * t2['bid']) * (1 - self.taker_fee)
        
        # Schritt 3: Coin C -> USDT (Verkauf zum Bid-Preis)
        final_a = (amount_c * t3['bid']) * (1 - self.taker_fee)
        
        profit_usd = final_a - amount
        profit_pct = (profit_usd / amount) * 100
        
        return profit_pct, profit_usd

    def save_result_to_csv(self, result_dict):
        with open(self.csv_file, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["scan", "route", "profit_pct", "profit_usd", "accepted"])
            writer.writerow(result_dict)

    def run(self):
        print(f"🔎 Starte {self.total_scans} Scans auf {self.exchange_name.upper()} (Fee: {self.taker_fee * 100}%)...")
        
        for scan in range(1, self.total_scans + 1):
            try:
                # KERN-OPTIMIERUNG: Nur 1 API-Aufruf pro Scan für ALLE Handelspaare
                all_tickers = self.exchange.fetch_tickers()
            except Exception as e:
                print(f"⚠️ Fehler beim Abrufen der Ticker in Scan {scan}: {e}")
                time.sleep(2)
                continue

            for route in self.routes:
                res = self.evaluate_route_from_tickers(route, self.trade_amount_usdt, all_tickers)
                if res:
                    pct, usd = res
                    route_str = " -> ".join(route)
                    accepted = pct >= self.min_profit_threshold
                    
                    self.save_result_to_csv({
                        "scan": scan,
                        "route": route_str,
                        "profit_pct": round(pct, 4),
                        "profit_usd": round(usd, 4),
                        "accepted": accepted
                    })
            
            print(f"⚡ Scan {scan}/{self.total_scans} abgeschlossen.")
            time.sleep(1)  # Kurze Pause zur Einhaltung der API-Limits
                
        print(f"\n✅ Analyse abgeschlossen. Ergebnisse in '{self.csv_file}' gespeichert.")

if __name__ == "__main__":
    # Bei Bedarf exchange_name auf "binance", "okx" oder "bitrue" ändern
    trader = PaperTrader(exchange_name="mexc", amount=10.0, threshold=0.01, scans=50)
    trader.run()
