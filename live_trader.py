import os
import time
import csv
import ccxt

class MultiExchangeLiveTrader:
    def __init__(self, amount_per_trade=10.0, min_profit_pct=0.10, dry_run=True):
        self.amount = amount_per_trade
        self.min_profit_pct = min_profit_pct
        self.max_profit_pct = 5.0
        self.dry_run = dry_run
        
        self.csv_file = "live_dry_run_results.csv"
        self.exchanges = {}

        # 1. OKX Setup (mit expliziter Domain-Einstellung)
        okx_key = os.getenv('OKX_API_KEY', '')
        if okx_key:
            self.exchanges['okx'] = {
                'instance': ccxt.okx({
                    'apiKey': okx_key,
                    'secret': os.getenv('OKX_API_SECRET', ''),
                    'password': os.getenv('OKX_PASSPRASE', ''),
                    'enableRateLimit': True,
                    'options': {
                        'defaultType': 'spot',
                    }
                }),
                'fee': 0.001
            }
            # Setze EU Hostname falls nötig
            self.exchanges['okx']['instance'].hostname = 'my.okx.com'

        # 2. Bitget Setup
        bitget_key = os.getenv('BITGET_API_KEY', '')
        if bitget_key:
            self.exchanges['bitget'] = {
                'instance': ccxt.bitget({
                    'apiKey': bitget_key,
                    'secret': os.getenv('BITGET_API_SECRET', ''),
                    'password': os.getenv('BITGET_PASSPRASE', ''),
                    'enableRateLimit': True,
                }),
                'fee': 0.001
            }

        self.init_csv()

    def init_csv(self):
        with open(self.csv_file, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "timestamp", "symbol", "buy_ex", "sell_ex", 
                "buy_price", "sell_price", "real_profit_pct", 
                "profit_usd", "min_amount_ok", "execution_mode", "status"
            ])
            writer.writeheader()

    def execute_arbitrage(self, symbol, buy_ex_name, sell_ex_name):
        buy_ex = self.exchanges[buy_ex_name]['instance']
        sell_ex = self.exchanges[sell_ex_name]['instance']

        try:
            ob_buy = buy_ex.fetch_order_book(symbol, limit=5)
            ob_sell = sell_ex.fetch_order_book(symbol, limit=5)

            if not ob_buy['asks'] or not ob_sell['bids']:
                return

            buy_price = ob_buy['asks'][0][0]
            sell_price = ob_sell['bids'][0][0]

            fee_buy = self.exchanges[buy_ex_name]['fee']
            fee_sell = self.exchanges[sell_ex_name]['fee']

            bought_coins = (self.amount / buy_price) * (1 - fee_buy)
            final_usdt = (bought_coins * sell_price) * (1 - fee_sell)
            
            real_profit_pct = ((final_usdt - self.amount) / self.amount) * 100
            profit_usd = final_usdt - self.amount

            if self.min_profit_pct <= real_profit_pct <= self.max_profit_pct:
                print(f"🔥 [DRY RUN] {symbol}: {buy_ex_name.upper()} -> {sell_ex_name.upper()} "
                      f"| Marge: +{real_profit_pct:.3f}% (+${profit_usd:.3f})")

                with open(self.csv_file, mode="a", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=[
                        "timestamp", "symbol", "buy_ex", "sell_ex", 
                        "buy_price", "sell_price", "real_profit_pct", 
                        "profit_usd", "min_amount_ok", "execution_mode", "status"
                    ])
                    writer.writerow({
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "symbol": symbol,
                        "buy_ex": buy_ex.upper(),
                        "sell_ex": sell_ex.upper(),
                        "buy_price": buy_price,
                        "sell_price": sell_price,
                        "real_profit_pct": round(real_profit_pct, 4),
                        "profit_usd": round(profit_usd, 4),
                        "min_amount_ok": True,
                        "execution_mode": "DRY_RUN",
                        "status": "EXECUTION_READY"
                    })

        except Exception:
            pass

    def run(self, cycles=5):
        print(f"🚀 Starte LIVE-Trader [DRY RUN] über Börsen: {', '.join([n.upper() for n in self.exchanges.keys()])}...")
        
        for name, data in self.exchanges.items():
            try:
                data['instance'].load_markets()
                print(f"✅ Märkte für {name.upper()} erfolgreich geladen ({len(data['instance'].markets)} Märkte).")
            except Exception as e:
                print(f"❌ Fehler beim Laden der Märkte für {name.upper()}: {e}")

        for cycle in range(1, cycles + 1):
            print(f"🔄 Scan-Zyklus {cycle}/{cycles}...")
            active = list(self.exchanges.keys())
            
            for i in range(len(active)):
                for j in range(len(active)):
                    if i != j:
                        ex1, ex2 = active[i], active[j]
                        try:
                            t1 = self.exchanges[ex1]['instance'].fetch_tickers()
                            t2 = self.exchanges[ex2]['instance'].fetch_tickers()

                            s1 = {s for s in t1.keys() if s.endswith('/USDT')}
                            s2 = {s for s in t2.keys() if s.endswith('/USDT')}
                            common = list(s1.intersection(s2))

                            print(f"  🔍 Vergleiche {len(common)} gemeinsame Handelspaare zwischen {ex1.upper()} und {ex2.upper()}...")

                            for symbol in common[:15]:  # Testweise die ersten 15 Paare scannen
                                self.execute_arbitrage(symbol, ex1, ex2)
                        except Exception as e:
                            print(f"⚠️ Fehler beim Pair-Fetch {ex1}-{ex2}: {e}")

            time.sleep(1)

if __name__ == "__main__":
    trader = MultiExchangeLiveTrader(amount_per_trade=10.0, min_profit_pct=0.05, dry_run=True)
    trader.run(cycles=3)
