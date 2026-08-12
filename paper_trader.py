import csv
import time
import ccxt

class PaperTrader:
    def __init__(self, exchange_name="mexc", amount=10.0, threshold=0.01, scans=50, **kwargs):
        self.exchange_name = exchange_name
        self.amount = amount
        self.min_profit_threshold = threshold
        self.total_scans = scans
        self.csv_file = "trading_results.csv"
        
        # MEXC Gebühren
        self.taker_fee = 0.0005 if exchange_name.lower() == "mexc" else 0.001  # 0.05% bei MEXC
        self.maker_fee = 0.0000 if exchange_name.lower() == "mexc" else 0.0002  # 0.00% bei MEXC
        
        self.exchange = getattr(ccxt, exchange_name)({'enableRateLimit': True})
        
        # CSV-Datei initialisieren
        with open(self.csv_file, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "scan", "route", "profit_pct", "profit_usd", "accepted", 
                "taker_profit_pct", "maker_profit_pct", "hybrid_profit_pct"
            ])
            writer.writeheader()

    def discover_dynamic_routes(self, tickers):
        """
        Sucht automatisch alle verfügbaren USDT-Dreiecks-Routen auf der Börse:
        USDT -> Coin B -> Coin C -> USDT
        """
        usdt_coins = set()
        for symbol in tickers.keys():
            if symbol.endswith('/USDT'):
                coin = symbol.split('/')[0]
                usdt_coins.add(coin)

        routes = []
        for symbol in tickers.keys():
            # Suche nach Paarungen zwischen zwei Coins, die beide gegen USDT gehandelt werden (z. B. BTC/ETH, DFI/BTC, PEPE/USDT etc.)
            if '/' in symbol and not symbol.endswith('/USDT') and not symbol.startswith('USDT/'):
                parts = symbol.split('/')
                coin_b, coin_c = parts[0], parts[1]
                
                if coin_b in usdt_coins and coin_c in usdt_coins:
                    routes.append(["USDT", coin_b, coin_c, "USDT"])

        print(f"💡 {len(routes)} dynamische Dreiecks-Routen auf {self.exchange_name.upper()} gefunden!")
        return routes

    def evaluate_all_strategies(self, route, amount, tickers):
        a, b, c, _ = route
        s1, s2, s3 = f"{b}/{a}", f"{b}/{c}", f"{c}/{a}"
        
        if not (s1 in tickers and s2 in tickers and s3 in tickers):
            return None
            
        t1, t2, t3 = tickers[s1], tickers[s2], tickers[s3]
        if not (t1.get('ask') and t1.get('bid') and 
                t2.get('ask') and t2.get('bid') and 
                t3.get('ask') and t3.get('bid')):
            return None

        # 1. Taker-Strategie (Market Orders)
        b_taker = (amount / t1['ask']) * (1 - self.taker_fee)
        c_taker = (b_taker * t2['bid']) * (1 - self.taker_fee)
        final_taker = (c_taker * t3['bid']) * (1 - self.taker_fee)
        taker_pct = ((final_taker - amount) / amount) * 100

        # 2. Maker-Strategie (Limit Orders)
        b_maker = (amount / t1['bid']) * (1 - self.maker_fee)
        c_maker = (b_maker * t2['ask']) * (1 - self.maker_fee)
        final_maker = (c_maker * t3['ask']) * (1 - self.maker_fee)
        maker_pct = ((final_maker - amount) / amount) * 100

        # 3. Hybrid-Strategie (Schritt 1: Limit, Schritt 2 & 3: Market)
        b_hybrid = (amount / t1['bid']) * (1 - self.maker_fee)
        c_hybrid = (b_hybrid * t2['bid']) * (1 - self.taker_fee)
        final_hybrid = (c_hybrid * t3['bid']) * (1 - self.taker_fee)
        hybrid_pct = ((final_hybrid - amount) / amount) * 100

        return taker_pct, maker_pct, hybrid_pct, final_hybrid - amount

    def run(self):
        print(f"🔎 Starte {self.total_scans} Scans auf {self.exchange_name.upper()}...")
        
        # Ersten Snapshot laden, um alle handelbaren Dreiecke zu erkennen
        try:
            initial_tickers = self.exchange.fetch_tickers()
            dynamic_routes = self.discover_dynamic_routes(initial_tickers)
        except Exception as e:
            print(f"❌ Fehler beim ersten Laden der Routen: {e}")
            return

        for scan in range(1, self.total_scans + 1):
            try:
                tickers = self.exchange.fetch_tickers()
            except Exception as e:
                print(f"⚠️ API-Fehler in Scan {scan}: {e}")
                time.sleep(2)
                continue

            found_profitable = 0
            for route in dynamic_routes:
                res = self.evaluate_all_strategies(route, self.amount, tickers)
                if res:
                    taker_pct, maker_pct, hybrid_pct, usd_diff = res
                    
                    # Um Speicherplatz zu sparen: Nur interessante Trades protokollieren (z. B. Maker oder Hybrid > -0.1%)
                    if maker_pct > 0 or hybrid_pct > -0.1:
                        route_str = " -> ".join(route)
                        accepted = hybrid_pct >= self.min_profit_threshold or maker_pct >= self.min_profit_threshold
                        
                        if accepted:
                            found_profitable += 1

                        with open(self.csv_file, mode="a", newline="", encoding="utf-8") as f:
                            writer = csv.DictWriter(f, fieldnames=[
                                "scan", "route", "profit_pct", "profit_usd", "accepted", 
                                "taker_profit_pct", "maker_profit_pct", "hybrid_profit_pct"
                            ])
                            writer.writerow({
                                "scan": scan,
                                "route": route_str,
                                "profit_pct": round(hybrid_pct, 4),
                                "profit_usd": round(usd_diff, 4),
                                "accepted": accepted,
                                "taker_profit_pct": round(taker_pct, 4),
                                "maker_profit_pct": round(maker_pct, 4),
                                "hybrid_profit_pct": round(hybrid_pct, 4)
                            })
            
            print(f"⚡ Scan {scan}/{self.total_scans} beendet. Profitable Chancen in diesem Scan: {found_profitable}")
            time.sleep(1)

        print(f"\n✅ Analyse abgeschlossen. CSV unter '{self.csv_file}' gespeichert.")

if __name__ == "__main__":
    trader = PaperTrader(exchange_name="mexc", amount=10.0, threshold=0.01, scans=50)
    trader.run()
