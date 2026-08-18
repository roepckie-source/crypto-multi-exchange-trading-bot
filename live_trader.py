import os
import time
import csv
import ccxt

class MultiExchangeLiveTrader:
    def __init__(self, amount_per_trade=10.0, min_profit_pct=0.02, dry_run=True):
        self.amount = amount_per_trade          # Einsatz pro Trade in USDT
        self.min_profit_pct = min_profit_pct    # Mindestgewinn in % (z. B. 0.02%)
        self.max_profit_pct = 5.0              # Safety-Cap gegen Ausreißer/Fake-Daten
        self.dry_run = dry_run                  # Safety Toggle: True = Dry Run
        
        self.csv_file = "live_dry_run_results.csv"
        self.exchanges = {}

        # 1. OKX Setup (EU-API Support)
        okx_key = os.getenv('OKX_API_KEY', '')
        if okx_key:
            self.exchanges['okx'] = {
                'instance': ccxt.okx({
                    'apiKey': okx_key,
                    'secret': os.getenv('OKX_API_SECRET', ''),
                    'password': os.getenv('OKX_PASSPRASE', ''),
                    'enableRateLimit': True,
                    'options': {'defaultType': 'spot'}
                }),
                'fee': 0.001
            }
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
        if not os.path.exists(self.csv_file):
            with open(self.csv_file, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=[
                    "timestamp", "symbol", "buy_ex", "sell_ex", 
                    "buy_price", "sell_price", "real_profit_pct", 
                    "profit_usd", "min_amount_ok", "execution_mode", "status"
                ])
                writer.writeheader()

    def execute_arbitrage(self, symbol, buy_ex_name, sell_ex_name, ticker_buy, ticker_sell):
        # Schneller Vor-Check über Ticker-Preise vor dem teuren Orderbuch-Fetch
        bid_sell = ticker_sell.get('bid')
        ask_buy = ticker_buy.get('ask')

        if not bid_sell or not ask_buy or ask_buy == 0:
            return

        raw_margin = ((bid_sell - ask_buy) / ask_buy) * 100
        if raw_margin < self.min_profit_pct:
            return

        # Wenn der Roh-Spread attraktiv ist, holen wir das echte Orderbuch zur Tiefenprüfung
        try:
            buy_ex = self.exchanges[buy_ex_name]['instance']
            sell_ex = self.exchanges[sell_ex_name]['instance']

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
                print(f"🔥 [DRY RUN GEFUNDEN] {symbol}: {buy_ex_name.upper()} -> {sell_ex_name.upper()} "
                      f"| Netto-Marge: +{real_profit_pct:.3f}% (+${profit_usd:.4f})")

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
                print(f"✅ Märkte für {name.upper()} geladen ({len(data['instance'].markets)} Märkte).")
            except Exception as e:
                print(f"❌ Fehler bei {name.upper()}: {e}")

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

                            for symbol in common:
                                ticker1 = t1.get(symbol, {})
                                ticker2 = t2.get(symbol, {})
                                self.execute_arbitrage(symbol, ex1, ex2, ticker1, ticker2)

                        except Exception as e:
                            print(f"⚠️ Fehler beim Pair-Fetch {ex1}-{ex2}: {e}")

            time.sleep(1)

if __name__ == "__main__":
    trader = MultiExchangeLiveTrader(amount_per_trade=10.0, min_profit_pct=0.02, dry_run=True)
    trader.run(cycles=5)
