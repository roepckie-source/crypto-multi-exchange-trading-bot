import os
import time
import csv
import ccxt

class MultiExchangeLiveTrader:
    def __init__(self, amount_per_trade=10.0, min_profit_pct=0.05, dry_run=True):
        self.amount = amount_per_trade          # Einsatz pro Trade in USDT (z.B. 10$)
        self.min_profit_pct = min_profit_pct    # Mindestgewinn in % (z. B. 0.05%)
        self.max_profit_pct = 3.0              # Safety-Cap gegen Slippage / Fake-Orderbücher
        self.dry_run = dry_run                  # ACHTUNG: False = ECHTE ORDERS!
        
        self.csv_file = "live_trading_results.csv"
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
                mode_str = "DRY_RUN" if self.dry_run else "LIVE_REAL_MONEY"
                print(f"🔥 [{mode_str}] {symbol}: {buy_ex_name.upper()} -> {sell_ex_name.upper()} "
                      f"| Netto: +{real_profit_pct:.3f}% (+${profit_usd:.4f})")

                status = "DETECTED"

                if not self.dry_run:
                    # ECHTE ORDERS AUSFÜHREN
                    print(f"⚡ FÜHRE ECHTE ORDERS AUS FÜR {symbol}...")
                    
                    # 1. Kaufen auf Börse 1
                    amount_to_buy = self.amount / buy_price
                    amount_formatted = buy_ex.amount_to_precision(symbol, amount_to_buy)
                    
                    buy_order = buy_ex.create_market_buy_order(symbol, amount_formatted)
                    print(f"✅ KAUF ERFOLGREICH auf {buy_ex_name.upper()}: {buy_order['id']}")

                    # tatsächliche Kaufmenge ermitteln
                    executed_amount = buy_order.get('filled', float(amount_formatted))

                    # 2. Verkaufen auf Börse 2
                    sell_amount_formatted = sell_ex.amount_to_precision(symbol, executed_amount)
                    sell_order = sell_ex.create_market_sell_order(symbol, sell_amount_formatted)
                    print(f"✅ VERKAUF ERFOLGREICH auf {sell_ex_name.upper()}: {sell_order['id']}")

                    status = "EXECUTED_SUCCESS"

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
                        "execution_mode": mode_str,
                        "status": status
                    })

        except Exception as e:
            print(f"❌ Fehler bei Order-Ausführung: {e}")

    def run(self, cycles=5):
        mode_label = "DRY RUN (SIMULATION)" if self.dry_run else "LIVE TRADING (ECHTGELD)"
        print(f"🚀 Starte Trader [{mode_label}] über: {', '.join([n.upper() for n in self.exchanges.keys()])}...")
        
        for name, data in self.exchanges.items():
            try:
                data['instance'].load_markets()
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
    # WICHTIG: Setze dry_run=False ERST WENN du bereit bist mit echtem Geld zu handeln!
    trader = MultiExchangeLiveTrader(
        amount_per_trade=10.0,   # Startkapital pro Trade (z.B. 10 USDT)
        min_profit_pct=0.08,     # Mindestgewinnschwelle für echte Trades (z.B. 0.08%)
        dry_run=True             # Vorher noch einmal testen mit True, dann auf False stellen!
    )
    trader.run(cycles=5)
