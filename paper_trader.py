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
        self.taker_fee = 0.0005 if exchange_name.lower() == "mexc" else 0.001  # 0.05%
        self.maker_fee = 0.0000 if exchange_name.lower() == "mexc" else 0.0002  # 0.00%
        
        self.exchange = getattr(ccxt, exchange_name)({'enableRateLimit': True})
        
        with open(self.csv_file, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "scan", "route", "profit_pct", "profit_usd", "accepted", 
                "taker_profit_pct", "maker_profit_pct", "hybrid_profit_pct", "depth_verified"
            ])
            writer.writeheader()

    def discover_dynamic_routes(self, tickers):
        usdt_coins = set()
        for symbol in tickers.keys():
            if symbol.endswith('/USDT'):
                coin = symbol.split('/')[0]
                usdt_coins.add(coin)

        routes = []
        for symbol in tickers.keys():
            if '/' in symbol and not symbol.endswith('/USDT') and not symbol.startswith('USDT/'):
                parts = symbol.split('/')
                coin_b, coin_c = parts[0], parts[1]
                if coin_b in usdt_coins and coin_c in usdt_coins:
                    routes.append(["USDT", coin_b, coin_c, "USDT"])

        print(f"💡 {len(routes)} dynamische Dreiecks-Routen auf {self.exchange_name.upper()} gefunden!")
        return routes

    def calculate_depth_cost(self, orderbook, amount_needed, is_buy=True):
        """
        Simuliert die Ausführung gegen das Orderbuch, um echten Durchschnittspreis (Slippage) zu ermitteln.
        """
        orders = orderbook['asks'] if is_buy else orderbook['bids']
        filled_amount = 0.0
        total_cost = 0.0

        for price, volume in orders:
            needed = amount_needed - filled_amount
            if volume >= needed:
                total_cost += needed * price if is_buy else needed * price
                filled_amount += needed
                break
            else:
                total_cost += volume * price if is_buy else volume * price
                filled_amount += volume

        # Wenn nicht genug Liquidität im Orderbuch liegt, ist der Trade ungültig
        if filled_amount < amount_needed:
            return None
        
        return total_cost / amount_needed  # Effekiver Durchschnittspreis

    def verify_route_depth(self, route, amount):
        """Prüft die tatsächliche Liquidität im Orderbuch für alle 3 Paare."""
        a, b, c, _ = route
        s1, s2, s3 = f"{b}/{a}", f"{b}/{c}", f"{c}/{a}"

        try:
            ob1 = self.exchange.fetch_order_book(s1, limit=10)
            ob2 = self.exchange.fetch_order_book(s2, limit=10)
            ob3 = self.exchange.fetch_order_book(s3, limit=10)

            # Schritt 1: USDT -> Coin B
            avg_price1 = self.calculate_depth_cost(ob1, amount, is_buy=True)
            if not avg_price1: return False, 0.0
            amount_b = (amount / avg_price1) * (1 - self.taker_fee)

            # Schritt 2: Coin B -> Coin C
            avg_price2 = self.calculate_depth_cost(ob2, amount_b, is_buy=False)
            if not avg_price2: return False, 0.0
            amount_c = (amount_b * avg_price2) * (1 - self.taker_fee)

            # Schritt 3: Coin C -> USDT
            avg_price3 = self.calculate_depth_cost(ob3, amount_c, is_buy=False)
            if not avg_price3: return False, 0.0
            final_a = (amount_c * avg_price3) * (1 - self.taker_fee)

            real_profit_pct = ((final_a - amount) / amount) * 100
            return True, real_profit_pct
        except Exception:
            return False, 0.0

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

        # Taker
        b_taker = (amount / t1['ask']) * (1 - self.taker_fee)
        c_taker = (b_taker * t2['bid']) * (1 - self.taker_fee)
        final_taker = (c_taker * t3['bid']) * (1 - self.taker_fee)
        taker_pct = ((final_taker - amount) / amount) * 100

        # Maker
        b_maker = (amount / t1['bid']) * (1 - self.maker_fee)
        c_maker = (b_maker * t2['ask']) * (1 - self.maker_fee)
        final_maker = (c_maker * t3['ask']) * (1 - self.maker_fee)
        maker_pct = ((final_maker - amount) / amount) * 100

        # Hybrid
        b_hybrid = (amount / t1['bid']) * (1 - self.maker_fee)
        c_hybrid = (b_hybrid * t2['bid']) * (1 - self.taker_fee)
        final_hybrid = (c_hybrid * t3['bid']) * (1 - self.taker_fee)
        hybrid_pct = ((final_hybrid - amount) / amount) * 100

        return taker_pct, maker_pct, hybrid_pct, final_hybrid - amount

    def run(self):
        print(f"🔎 Starte {self.total_scans} Scans auf {self.exchange_name.upper()}...")
        
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

            found_verified = 0
            for route in dynamic_routes:
                res = self.evaluate_all_strategies(route, self.amount, tickers)
                if res:
                    taker_pct, maker_pct, hybrid_pct, usd_diff = res
                    
                    # Tiefenprüfung NUR ausführen, wenn die Ticker-Daten Gewinne versprechen
                    if maker_pct > 0.1 or hybrid_pct > 0.0:
                        depth_ok, real_pct = self.verify_route_depth(route, self.amount)
                        
                        # Ein Signal gilt nur als voll akzeptiert, wenn die Tiefenprüfung positiv ist
                        accepted = depth_ok and real_pct >= self.min_profit_threshold
                        
                        if accepted:
                            found_verified += 1

                        route_str = " -> ".join(route)
                        with open(self.csv_file, mode="a", newline="", encoding="utf-8") as f:
                            writer = csv.DictWriter(f, fieldnames=[
                                "scan", "route", "profit_pct", "profit_usd", "accepted", 
                                "taker_profit_pct", "maker_profit_pct", "hybrid_profit_pct", "depth_verified"
                            ])
                            writer.writerow({
                                "scan": scan,
                                "route": route_str,
                                "profit_pct": round(real_pct if depth_ok else hybrid_pct, 4),
                                "profit_usd": round(usd_diff, 4),
                                "accepted": accepted,
                                "taker_profit_pct": round(taker_pct, 4),
                                "maker_profit_pct": round(maker_pct, 4),
                                "hybrid_profit_pct": round(hybrid_pct, 4),
                                "depth_verified": depth_ok
                            })
            
            print(f"⚡ Scan {scan}/{self.total_scans} beendet. In der Tiefe verifizierte echte Chancen: {found_verified}")
            time.sleep(1)

        print(f"\n✅ Analyse abgeschlossen. CSV unter '{self.csv_file}' gespeichert.")

if __name__ == "__main__":
    trader = PaperTrader(exchange_name="mexc", amount=10.0, threshold=0.01, scans=50)
    trader.run()
