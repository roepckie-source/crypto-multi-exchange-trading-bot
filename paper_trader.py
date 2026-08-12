import csv
import time
import ccxt

class PaperTrader:
    def __init__(self, amount=10.0, threshold=0.01, scans=50, **kwargs):
        self.amount = amount
        self.min_profit_threshold = threshold
        self.total_scans = scans
        self.csv_file = "trading_results.csv"

        # Wir vergleichen MEXC (niedrige Gebühren) mit Binance & Gate.io
        self.exchanges = {
            'mexc': {'instance': ccxt.mexc({'enableRateLimit': True}), 'fee': 0.0005},
            'binance': {'instance': ccxt.binance({'enableRateLimit': True}), 'fee': 0.001},
            'gateio': {'instance': ccxt.gateio({'enableRateLimit': True}), 'fee': 0.002}
        }

        # CSV Header anpassen
        with open(self.csv_file, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "scan", "symbol", "buy_exchange", "sell_exchange", 
                "buy_price", "sell_price", "profit_pct", "profit_usd", "accepted"
            ])
            writer.writeheader()

    def discover_common_symbols(self, ex1_tickers, ex2_tickers):
        """Findet alle gemeinsamen USDT-Handelspaare auf zwei Börsen."""
        syms1 = {s for s in ex1_tickers.keys() if s.endswith('/USDT')}
        syms2 = {s for s in ex2_tickers.keys() if s.endswith('/USDT')}
        return list(syms1.intersection(syms2))

    def evaluate_cross_arbitrage(self, symbol, ex_buy_name, ex_buy_data, ex_sell_name, ex_sell_data):
        """Berechnet Arbitrage-Gewinn: Kaufen auf Börse A (Ask), Verkaufen auf Börse B (Bid)."""
        ticker_buy = ex_buy_data.get(symbol)
        ticker_sell = ex_sell_data.get(symbol)

        if not ticker_buy or not ticker_sell:
            return None

        ask_price = ticker_buy.get('ask')  # Kaufpreis auf Börse A
        bid_price = ticker_sell.get('bid') # Verkaufspreis auf Börse B

        if not ask_price or not bid_price or ask_price <= 0 or bid_price <= 0:
            return None

        fee_buy = self.exchanges[ex_buy_name]['fee']
        fee_sell = self.exchanges[ex_sell_name]['fee']

        # Schritt 1: Kaufen auf Börse A
        bought_coins = (self.amount / ask_price) * (1 - fee_buy)

        # Schritt 2: Verkaufen auf Börse B
        final_usdt = (bought_coins * bid_price) * (1 - fee_sell)

        profit_usd = final_usdt - self.amount
        profit_pct = (profit_usd / self.amount) * 100

        return {
            'symbol': symbol,
            'buy_ex': ex_buy_name.upper(),
            'sell_ex': ex_sell_name.upper(),
            'buy_price': ask_price,
            'sell_price': bid_price,
            'profit_pct': profit_pct,
            'profit_usd': profit_usd,
            'accepted': profit_pct >= self.min_profit_threshold
        }

    def run(self):
        print("🔎 Starte Cross-Exchange-Arbitrage-Scan...")

        # Paare von Börsen vergleichen: (MEXC vs Binance, MEXC vs Gate.io)
        exchange_pairs = [
            ('mexc', 'binance'),
            ('mexc', 'gateio')
        ]

        for scan in range(1, self.total_scans + 1):
            print(f"⚡ Scan {scan}/{self.total_scans} wird ausgeführt...")

            # Tickers von allen Börsen laden
            tickers_cache = {}
            for name, data in self.exchanges.items():
                try:
                    tickers_cache[name] = data['instance'].fetch_tickers()
                except Exception as e:
                    print(f"⚠️ Fehler beim Laden von {name}: {e}")
                    tickers_cache[name] = {}

            found_opportunities = 0

            for ex1_name, ex2_name in exchange_pairs:
                t1 = tickers_cache.get(ex1_name, {})
                t2 = tickers_cache.get(ex2_name, {})

                if not t1 or not t2:
                    continue

                common_symbols = self.discover_common_symbols(t1, t2)

                for symbol in common_symbols:
                    # Richtung 1: Kaufen auf Ex1 -> Verkaufen auf Ex2
                    res1 = self.evaluate_cross_arbitrage(symbol, ex1_name, t1, ex2_name, t2)
                    # Richtung 2: Kaufen auf Ex2 -> Verkaufen auf Ex1
                    res2 = self.evaluate_cross_arbitrage(symbol, ex2_name, t2, ex1_name, t1)

                    for res in [res1, res2]:
                        if res and res['profit_pct'] > -0.2:  # Nur relevante Trades protokollieren
                            if res['accepted']:
                                found_opportunities += 1

                            with open(self.csv_file, mode="a", newline="", encoding="utf-8") as f:
                                writer = csv.DictWriter(f, fieldnames=[
                                    "scan", "symbol", "buy_exchange", "sell_exchange", 
                                    "buy_price", "sell_price", "profit_pct", "profit_usd", "accepted"
                                ])
                                writer.writerow({
                                    "scan": scan,
                                    "symbol": res['symbol'],
                                    "buy_exchange": res['buy_ex'],
                                    "sell_exchange": res['sell_ex'],
                                    "buy_price": res['buy_price'],
                                    "sell_price": res['sell_price'],
                                    "profit_pct": round(res['profit_pct'], 4),
                                    "profit_usd": round(res['profit_usd'], 4),
                                    "accepted": res['accepted']
                                })

            print(f"   -> Profitable Cross-Exchange Chancen in Scan {scan}: {found_opportunities}")
            time.sleep(1)

        print(f"\n✅ Analyse abgeschlossen. Ergebnisse in '{self.csv_file}' gespeichert.")

if __name__ == "__main__":
    trader = PaperTrader(amount=10.0, threshold=0.01, scans=50)
    trader.run()
