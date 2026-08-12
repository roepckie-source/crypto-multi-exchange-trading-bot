import csv
import time
import ccxt

class MakerPaperTrader:
    def __init__(self, exchange_name="mexc", amount=10.0, scans=20):
        self.exchange_name = exchange_name
        self.amount = amount
        self.total_scans = scans
        self.csv_file = "maker_vs_taker_results.csv"
        
        # MEXC Gebühren
        self.taker_fee = 0.0005  # 0.05%
        self.maker_fee = 0.0000  # 0.00%
        
        self.exchange = getattr(ccxt, exchange_name)({'enableRateLimit': True})
        
        self.routes = [
            ["USDT", "DFI", "BTC", "USDT"],
            ["USDT", "ETH", "BTC", "USDT"],
            ["USDT", "XRP", "BTC", "USDT"],
            ["USDT", "LTC", "BTC", "USDT"],
        ]
        
        with open(self.csv_file, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["scan", "route", "taker_profit_pct", "maker_profit_pct", "hybrid_profit_pct"])
            writer.writeheader()

    def evaluate_all_strategies(self, route, amount, tickers):
        a, b, c, _ = route
        s1, s2, s3 = f"{b}/{a}", f"{b}/{c}", f"{c}/{a}"
        
        if not (s1 in tickers and s2 in tickers and s3 in tickers):
            return None
            
        t1, t2, t3 = tickers[s1], tickers[s2], tickers[s3]
        if not (t1.get('ask') and t2.get('bid') and t3.get('bid')):
            return None

        # ---------------------------------------------------------
        # 1. REINE TAKER-STRATEGIE (Kauf zu Ask, Verkauf zu Bid)
        # ---------------------------------------------------------
        b_taker = (amount / t1['ask']) * (1 - self.taker_fee)
        c_taker = (b_taker * t2['bid']) * (1 - self.taker_fee)
        final_taker = (c_taker * t3['bid']) * (1 - self.taker_fee)
        taker_pct = ((final_taker - amount) / amount) * 100

        # ---------------------------------------------------------
        # 2. REINE MAKER-STRATEGIE (Kauf zu Bid, Verkauf zu Ask)
        # ---------------------------------------------------------
        b_maker = (amount / t1['bid']) * (1 - self.maker_fee)
        c_maker = (b_maker * t2['ask']) * (1 - self.maker_fee)
        final_maker = (c_maker * t3['ask']) * (1 - self.maker_fee)
        maker_pct = ((final_maker - amount) / amount) * 100

        # ---------------------------------------------------------
        # 3. HYBRID-STRATEGIE (Leg 1: Maker, Leg 2 & 3: Taker)
        # ---------------------------------------------------------
        b_hybrid = (amount / t1['bid']) * (1 - self.maker_fee)
        c_hybrid = (b_hybrid * t2['bid']) * (1 - self.taker_fee)
        final_hybrid = (c_hybrid * t3['bid']) * (1 - self.taker_fee)
        hybrid_pct = ((final_hybrid - amount) / amount) * 100

        return taker_pct, maker_pct, hybrid_pct

    def run(self):
        print(f"🔎 Starte Maker-Vergleichsscans auf {self.exchange_name.upper()}...")
        
        for scan in range(1, self.total_scans + 1):
            try:
                tickers = self.exchange.fetch_tickers()
            except Exception as e:
                print(f"⚠️ API-Fehler in Scan {scan}: {e}")
                time.sleep(2)
                continue

            for route in self.routes:
                res = self.evaluate_all_strategies(route, self.amount, tickers)
                if res:
                    taker_pct, maker_pct, hybrid_pct = res
                    route_str = " -> ".join(route)
                    
                    with open(self.csv_file, mode="a", newline="", encoding="utf-8") as f:
                        writer = csv.DictWriter(f, fieldnames=["scan", "route", "taker_profit_pct", "maker_profit_pct", "hybrid_profit_pct"])
                        writer.writerow({
                            "scan": scan,
                            "route": route_str,
                            "taker_profit_pct": round(taker_pct, 4),
                            "maker_profit_pct": round(maker_pct, 4),
                            "hybrid_profit_pct": round(hybrid_pct, 4)
                        })
            
            print(f"⚡ Scan {scan}/{self.total_scans} verarbeitet.")
            time.sleep(1)

if __name__ == "__main__":
    trader = MakerPaperTrader(exchange_name="mexc", amount=10.0, scans=20)
    trader.run()
