import csv
import time
import ccxt

class PaperTrader:
    def __init__(self, amount=10.0, threshold=0.01, scans=25, **kwargs):
        self.amount = amount
        self.min_profit_threshold = threshold
        self.max_profit_threshold = 5.0      # Maximal realistischer Gewinn (+5 %)
        self.max_price_ratio = 1.5           # Max. erlaubte Preisabweichung (Faktor 1.5)
        self.total_scans = scans
        self.csv_file = "trading_results.csv"

        # Binance entfernt, da GitHub-Server (US-IPs) von Binance geblockt werden
        self.exchanges = {
            'mexc': {'instance': ccxt.mexc({'enableRateLimit': True}), 'fee': 0.0005},
            'gate': {'instance': ccxt.gate({'enableRateLimit': True}), 'fee': 0.002}
        }

        with open(self.csv_file, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "scan", "symbol", "buy_exchange", "sell_exchange", 
                "buy_price", "sell_price", "profit_pct", "profit_usd", 
                "accepted", "depth_verified", "real_profit_pct", "status_note"
            ])
            writer.writeheader()

    def discover_common_symbols(self, ex1_tickers, ex2_tickers):
        syms1 = {s for s in ex1_tickers.keys() if s.endswith('/USDT')}
        syms2 = {s for s in ex2_tickers.keys() if s.endswith('/USDT')}
        return list(syms1.intersection(syms2))

    def calculate_depth_cost(self, orderbook, amount_needed, is_buy=True):
        orders = orderbook['asks'] if is_buy else orderbook['bids']
        filled_amount = 0.0
        total_cost = 0.0

        for price, volume in orders:
            needed = amount_needed - filled_amount
            if volume >= needed:
                total_cost += needed * price
                filled_amount += needed
                break
            else:
                total_cost += volume * price
                filled_amount += volume

        if filled_amount < amount_needed:
            return None
        
        return total_cost / amount_needed

    def verify_orderbook_depth(self, symbol, ex_buy_name, ex_sell_name):
        try:
            ex_buy = self.exchanges[ex_buy_name]['instance']
            ex_sell = self.exchanges[ex_sell_name]['instance']

            ob_buy = ex_buy.fetch_order_book(symbol, limit=10)
            ob_sell = ex_sell.fetch_order_book(symbol, limit=10)

            avg_buy_price = self.calculate_depth_cost(ob_buy, self.amount, is_buy=True)
            if not avg_buy_price:
                return False, 0.0

            fee_buy = self.exchanges[ex_buy_name]['fee']
            fee_sell = self.exchanges[ex_sell_name]['fee']

            bought_coins = (self.amount / avg_buy_price) * (1 - fee_buy)
            avg_sell_price = self.calculate_depth_cost(ob_sell, bought_coins, is_buy=False)

            if not avg_sell_price:
                return False, 0.0

            final_usdt = (bought_coins * avg_sell_price) * (1 - fee_sell)
            real_pct = ((final_usdt - self.amount) / self.amount) * 100

            return True, real_pct
        except Exception:
            return False, 0.0

    def evaluate_cross_arbitrage(self, symbol, ex_buy_name, ex_buy_data, ex_sell_name, ex_sell_data):
        ticker_buy = ex_buy_data.get(symbol)
        ticker_sell = ex_sell_data.get(symbol)

        if not ticker_buy or not ticker_sell:
            return None

        ask_price = ticker_buy.get('ask')
        bid_price = ticker_sell.get('bid')

        if not ask_price or not bid_price or ask_price <= 0 or bid_price <= 0:
            return None

        price_ratio = bid_price / ask_price
        if price_ratio > self.max_price_ratio or price_ratio < (1 / self.max_price_ratio):
            return None

        fee_buy = self.exchanges[ex_buy_name]['fee']
        fee_sell = self.exchanges[ex_sell_name]['fee']

        bought_coins = (self.amount / ask_price) * (1 - fee_buy)
        final_usdt = (bought_coins * bid_price) * (1 - fee_sell)

        profit_usd = final_usdt - self.amount
        profit_pct = (profit_usd / self.amount) * 100

        is_realistic = profit_pct <= self.max_profit_threshold

        return {
            'symbol': symbol,
            'buy_ex': ex_buy_name,
            'sell_ex': ex_sell_name,
            'buy_price': ask_price,
            'sell_price': bid_price,
            'profit_pct': profit_pct,
            'profit_usd': profit_usd,
            'accepted': (profit_pct >= self.min_profit_threshold) and is_realistic
        }

    def print_summary(self, total_trades, total_profit_usd, valid_trades_list):
        print("\n" + "="*60)
        print("📊 SESSION SUMMARY & ARBITRAGE REPORT")
        print("="*60)
        print(f"Eingesetztes Kapital pro Trade:  ${self.amount:.2f} USD")
        print(f"Gefundene valide Trades:        {total_trades}")
        
        if total_trades > 0:
            avg_profit_pct = sum(t['pct'] for t in valid_trades_list) / total_trades
            avg_profit_usd = sum(t['usd'] for t in valid_trades_list) / total_trades
            print(f"Akkumulierter Gesamtertrag:     +${total_profit_usd:.4f} USD")
            print(f"Durchschnittlicher Gewinn:       +{avg_profit_pct:.3f}% (+${avg_profit_usd:.4f} USD)")
            print("\nTOP 5 TRADES DES RUNS:")
            sorted_trades = sorted(valid_trades_list, key=lambda x: x['pct'], reverse=True)[:5]
            for i, t in enumerate(sorted_trades, 1):
                print(f"  {i}. {t['symbol']} ({t['buy']} -> {t['sell']}): +{t['pct']:.2f}% (+${t['usd']:.4f})")
        else:
            print("Keine verifizierten VALID_TRADES in dieser Session gefunden.")
        print("="*60 + "\n")

    def run(self):
        print("🔎 Starte Cross-Exchange-Arbitrage-Scan (MEXC <-> Gate.io)...")

        exchange_pairs = [
            ('mexc', 'gate')
        ]

        total_valid_trades = 0
        total_session_profit_usd = 0.0
        valid_trades_list = []

        for scan in range(1, self.total_scans + 1):
            print(f"⚡ Scan {scan}/{self.total_scans} wird ausgeführt...")

            tickers_cache = {}
            for name, data in self.exchanges.items():
                try:
                    tickers_cache[name] = data['instance'].fetch_tickers()
                except Exception as e:
                    print(f"⚠️ Fehler beim Laden von {name}: {e}")
                    tickers_cache[name] = {}

            found_verified = 0

            for ex1_name, ex2_name in exchange_pairs:
                t1 = tickers_cache.get(ex1_name, {})
                t2 = tickers_cache.get(ex2_name, {})

                if not t1 or not t2:
                    continue

                common_symbols = self.discover_common_symbols(t1, t2)

                for symbol in common_symbols:
                    res1 = self.evaluate_cross_arbitrage(symbol, ex1_name, t1, ex2_name, t2)
                    res2 = self.evaluate_cross_arbitrage(symbol, ex2_name, t2, ex1_name, t1)

                    for res in [res1, res2]:
                        if res and res['profit_pct'] > -0.2:
                            depth_ok = False
                            real_pct = 0.0
                            accepted_final = False
                            status = "OK"

                            if res['accepted']:
                                depth_ok, real_pct = self.verify_orderbook_depth(
                                    res['symbol'], res['buy_ex'], res['sell_ex']
                                )
                                is_valid = (
                                    depth_ok and 
                                    self.min_profit_threshold <= real_pct <= self.max_profit_threshold
                                )
                                if is_valid:
                                    found_verified += 1
                                    accepted_final = True
                                    status = "VALID_TRADE"

                                    real_profit_usd = (self.amount * real_pct) / 100
                                    total_valid_trades += 1
                                    total_session_profit_usd += real_profit_usd
                                    valid_trades_list.append({
                                        'symbol': res['symbol'],
                                        'buy': res['buy_ex'].upper(),
                                        'sell': res['sell_ex'].upper(),
                                        'pct': real_pct,
                                        'usd': real_profit_usd
                                    })
                                else:
                                    status = "DEPTH_FAILED_OR_OUTLIER"

                            with open(self.csv_file, mode="a", newline="", encoding="utf-8") as f:
                                writer = csv.DictWriter(f, fieldnames=[
                                    "scan", "symbol", "buy_exchange", "sell_exchange", 
                                    "buy_price", "sell_price", "profit_pct", "profit_usd", 
                                    "accepted", "depth_verified", "real_profit_pct", "status_note"
                                ])
                                writer.writerow({
                                    "scan": scan,
                                    "symbol": res['symbol'],
                                    "buy_exchange": res['buy_ex'].upper(),
                                    "sell_exchange": res['sell_ex'].upper(),
                                    "buy_price": res['buy_price'],
                                    "sell_price": res['sell_price'],
                                    "profit_pct": round(res['profit_pct'], 4),
                                    "profit_usd": round(res['profit_usd'], 4),
                                    "accepted": accepted_final,
                                    "depth_verified": depth_ok,
                                    "real_profit_pct": round(real_pct, 4) if depth_ok else 0.0,
                                    "status_note": status
                                })

            print(f"   -> Echte verifizierte Chancen in Scan {scan}: {found_verified}")
            time.sleep(1)

        print(f"\n✅ Analyse abgeschlossen. Ergebnisse in '{self.csv_file}' gespeichert.")
        self.print_summary(total_valid_trades, total_session_profit_usd, valid_trades_list)

if __name__ == "__main__":
    trader = PaperTrader(amount=10.0, threshold=0.01, scans=25)
    trader.run()
