import os
import time
import csv
import ccxt

class MultiExchangePaperTrader:
    def __init__(self, amount_per_trade=10.0, min_profit_pct=0.02, dry_run=True):
        self.amount = amount_per_trade          # Simulierter Einsatz in USDT
        self.min_profit_pct = min_profit_pct    # Mindestgewinnschwelle in %
        self.max_profit_pct = 5.0              # Safety-Cap gegen Ausreißer
        self.dry_run = dry_run                  # Im Paper Trading immer True
        
        self.csv_file = "paper_trading_results.csv"
        self.exchanges = {}

        # 1. OKX Setup (EU-API Domain)
        okx_key = os.getenv('OKX_API_KEY', '')
        if okx_key:
            try:
                ex = ccxt.okx({
                    'apiKey': okx_key,
                    'secret': os.getenv('OKX_API_SECRET', ''),
                    'password': os.getenv('OKX_PASSPRASE', ''),
                    'enableRateLimit': True,
                    'options': {'defaultType': 'spot'}
                })
                ex.hostname = 'my.okx.com'
                self.exchanges['okx'] = {'instance': ex, 'fee': 0.001}
            except Exception as e:
                print(f"⚠️ OKX Initialisierungsfehler: {e}")

        # 2. Bitget Setup
        bitget_key = os.getenv('BITGET_API_KEY', '')
        if bitget_key:
            try:
                ex = ccxt.bitget({
                    'apiKey': bitget_key,
                    'secret': os.getenv('BITGET_API_SECRET', ''),
                    'password': os.getenv('BITGET_PASSPRASE', ''),
                    'enableRateLimit': True,
                })
                self.exchanges['bitget'] = {'instance': ex, 'fee': 0.001}
            except Exception as e:
                print(f"⚠️ Bitget Initialisierungsfehler: {e}")

        self.init_csv()

    def init_csv(self):
        if not os.path.exists(self.csv_file):
            with open(self.csv_file, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=[
                    "timestamp", "symbol", "buy_ex", "sell_ex", 
                    "buy_price", "sell_price", "real_profit_pct", 
                    "profit_usd", "execution_mode", "status"
                ])
                writer.writeheader()

    def execute_arbitrage(self, symbol, buy_ex_name, sell_ex_name, ticker_buy, ticker_sell):
        bid_sell = ticker_sell.get('bid')
        ask_buy = ticker_buy.get('ask')

        if not bid_sell or not ask_buy or ask_buy == 0:
            return

        raw_margin = ((bid_sell - ask_buy) / ask_buy) * 100
        if raw_margin < self.min_profit_pct:
            return

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
                print(f"🔥 [PAPER TRADE GEFUNDEN] {symbol}: {buy_ex_name.upper()} -> {sell_ex_name.upper()} "
                      f"| Marge: +{real_profit_pct:.3f}% (+${profit_usd:.4f})")

                with open(self.csv_file, mode="a", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=[
                        "timestamp", "symbol", "buy_ex", "sell_ex", 
                        "buy_price", "sell_price", "real_profit_pct", 
                        "profit_usd", "execution_mode", "status"
                    ])
                    writer.writerow({
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "symbol": symbol,
                        "buy_ex": buy_ex_name.upper(),
                        "sell_ex": sell_ex_name.upper(),
                        "buy_price": buy_price,
                        "sell_price": sell_price,
                        "real_profit_pct": round(real_profit_pct, 4),
                        "profit_usd": round(profit_usd, 4),
                        "execution_mode": "PAPER_TRADING",
                        "status": "SIMULATED_READY"
                    })

        except Exception:
            pass

    def run_continuous(self, duration_hours=6, delay_seconds=3):
        """ Längerer Testlauf über mehrere Stunden """
        print(f"🚀 Starte LÄNGEREN PAPER TRADING RUN...")
        print(f"⏱️ Laufzeit: ca. {duration_hours} Stunden | Pause zwischen Scans: {delay_seconds} Sekunden.")
        
        for name, data in self.exchanges.items():
            try:
                data['instance'].load_markets()
                print(f"✅ Märkte geladen für {name.upper()}: {len(data['instance'].markets)} Märkte")
            except Exception as e:
                print(f"⚠️ Warnung bei {name.upper()}: {e}")

        start_time = time.time()
        end_time = start_time + (duration_hours * 3600)
        cycle = 1

        while time.time() < end_time:
            print(f"🔄 Scan-Zyklus {cycle} | Verstrichene Zeit: {int((time.time() - start_time) / 60)} Min.")
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
                            print(f"⚠️ Fehler beim Pair-Fetch ({ex1}-{ex2}): {e}")

            cycle += 1
            time.sleep(delay_seconds)

        print("🏁 Paper Trading Testlauf erfolgreich beendet!")

if __name__ == "__main__":
    trader = MultiExchangePaperTrader(
        amount_per_trade=10.0,   # Simulierter Einsatz
        min_profit_pct=0.02,     # Mindestmarge (+0.02%)
        dry_run=True             # Reine Simulation
    )
    # Dauer in Stunden (z. B. 1 Stunde für GitHub Actions Runner Max-Time)
    trader.run_continuous(duration_hours=1, delay_seconds=2)
