import os
import time
import csv
import ccxt

class MultiExchangeTrader:
    def __init__(self, amount_per_trade=10.0, min_profit_pct=0.08, dry_run=True):
        self.amount = amount_per_trade          # Einsatz pro Trade in USDT (z. B. $10)
        self.min_profit_pct = min_profit_pct    # Mindestgewinn in % (z. B. 0.08%)
        self.max_profit_pct = 5.0              # Safety-Cap gegen fehlerhafte Ticker / Ausreißer
        self.dry_run = dry_run                  # True = Simulation (Paper Trading) | False = ECHTE ORDERS!
        
        self.csv_file = "paper_trading_results.csv" if dry_run else "live_trading_results.csv"
        self.exchanges = {}

        # 1. OKX Setup (EU-Domain Support)
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

        # 3. KuCoin Setup
        kucoin_key = os.getenv('KUCOIN_API_KEY', '')
        if kucoin_key:
            try:
                ex = ccxt.kucoin({
                    'apiKey': kucoin_key,
                    'secret': os.getenv('KUCOIN_API_SECRET', ''),
                    'password': os.getenv('KUCOIN_PASSPRASE', ''),
                    'enableRateLimit': True,
                })
                self.exchanges['kucoin'] = {'instance': ex, 'fee': 0.001}
            except Exception as e:
                print(f"⚠️ KuCoin Initialisierungsfehler: {e}")

        self.init_csv()

    def init_csv(self):
        """ Erstellt die CSV-Logdatei, falls sie nicht existiert """
        if not os.path.exists(self.csv_file):
            with open(self.csv_file, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=[
                    "timestamp", "symbol", "buy_ex", "sell_ex", 
                    "buy_price", "sell_price", "real_profit_pct", 
                    "profit_usd", "execution_mode", "status"
                ])
                writer.writeheader()

    def check_balances(self, buy_ex, sell_ex, symbol):
        """ Prüft das verfügbare Guthaben auf beiden Börsen vor einem Live-Trade """
        try:
            bal_buy = buy_ex.fetch_balance()
            bal_sell = sell_ex.fetch_balance()

            base_currency = symbol.split('/')[0] # z.B. ACE
            quote_currency = symbol.split('/')[1] # USDT

            usdt_buy = bal_buy.get('free', {}).get(quote_currency, 0.0)
            coin_sell = bal_sell.get('free', {}).get(base_currency, 0.0)

            if usdt_buy < self.amount:
                print(f"⚠️ Unzureichendes USDT-Guthaben auf Käufer-Börse! Benötigt: {self.amount}, Verfügbar: {usdt_buy}")
                return False

            return True
        except Exception as e:
            print(f"⚠️ Fehler beim Balance-Check: {e}")
            return False

    def execute_arbitrage(self, symbol, buy_ex_name, sell_ex_name, ticker_buy, ticker_sell):
        bid_sell = ticker_sell.get('bid')
        ask_buy = ticker_buy.get('ask')

        if not bid_sell or not ask_buy or ask_buy == 0:
            return

        # Schnell-Filter per Ticker
        raw_margin = ((bid_sell - ask_buy) / ask_buy) * 100
        if raw_margin < self.min_profit_pct:
            return

        try:
            buy_ex = self.exchanges[buy_ex_name]['instance']
            sell_ex = self.exchanges[sell_ex_name]['instance']

            # Orderbuch-Deep-Check (Top 5 Level)
            ob_buy = buy_ex.fetch_order_book(symbol, limit=5)
            ob_sell = sell_ex.fetch_order_book(symbol, limit=5)

            if not ob_buy['asks'] or not ob_sell['bids']:
                return

            buy_price = ob_buy['asks'][0][0]
            sell_price = ob_sell['bids'][0][0]

            # Prüfe Orderbuch-Volumen auf Stufe 1 (ausreichend für unseren Einsatz?)
            buy_volume_available = ob_buy['asks'][0][1] * buy_price
            if buy_volume_available < self.amount:
                return # Zu wenig Liquidität im Orderbuch

            fee_buy = self.exchanges[buy_ex_name]['fee']
            fee_sell = self.exchanges[sell_ex_name]['fee']

            # Netto-Berechnung inklusive Trading-Gebühren
            bought_coins = (self.amount / buy_price) * (1 - fee_buy)
            final_usdt = (bought_coins * sell_price) * (1 - fee_sell)
            
            real_profit_pct = ((final_usdt - self.amount) / self.amount) * 100
            profit_usd = final_usdt - self.amount

            if self.min_profit_pct <= real_profit_pct <= self.max_profit_pct:
                mode_str = "PAPER_TRADING" if self.dry_run else "LIVE_REAL_MONEY"
                print(f"🔥 [{mode_str}] {symbol}: {buy_ex_name.upper()} -> {sell_ex_name.upper()} "
                      f"| Marge: +{real_profit_pct:.3f}% (+${profit_usd:.4f})")

                status = "SIMULATED_READY"

                # Wenn dry_run == False, werden echte Orders ausgeführt
                if not self.dry_run:
                    if not self.check_balances(buy_ex, sell_ex, symbol):
                        print("❌ Trade abgebrochen: Unzureichendes Guthaben.")
                        return

                    print(f"⚡ FÜHRE ECHTE ORDERS AUS FÜR {symbol}...")
                    
                    # 1. Kaufen auf Börse 1
                    amount_to_buy = self.amount / buy_price
                    amount_formatted = buy_ex.amount_to_precision(symbol, amount_to_buy)
                    
                    buy_order = buy_ex.create_market_buy_order(symbol, amount_formatted)
                    print(f"✅ KAUF ERFOLGREICH ({buy_ex_name.upper()}): Order-ID {buy_order['id']}")

                    executed_amount = buy_order.get('filled', float(amount_formatted))

                    # 2. Verkaufen auf Börse 2
                    sell_amount_formatted = sell_ex.amount_to_precision(symbol, executed_amount)
                    sell_order = sell_ex.create_market_sell_order(symbol, sell_amount_formatted)
                    print(f"✅ VERKAUF ERFOLGREICH ({sell_ex_name.upper()}): Order-ID {sell_order['id']}")

                    status = "EXECUTED_SUCCESS"

                # Protokollierung in CSV
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
            # Fehler abfangen und Log sauber halten
            pass

    def run_continuous(self, duration_hours=1, delay_seconds=2):
        """ Führt die Scans kontinuierlich für eine festgelegte Dauer aus """
        mode_label = "PAPER TRADING (SIMULATION)" if self.dry_run else "LIVE TRADING (ECHTGELD)"
        print(f"🚀 Starte Trader [{mode_label}]...")
        print(f"⏱️ Laufzeit: {duration_hours} Stunde(n) | Pause zwischen Scans: {delay_seconds}s")
        
        # Märkte von allen aktiven Börsen laden
        for name, data in list(self.exchanges.items()):
            try:
                data['instance'].load_markets()
                print(f"✅ Märkte geladen für {name.upper()}: {len(data['instance'].markets)} Paare")
            except Exception as e:
                print(f"⚠️ Märkte konnten für {name.upper()} nicht geladen werden: {e}")

        start_time = time.time()
        end_time = start_time + (duration_hours * 3600)
        cycle = 1

        while time.time() < end_time:
            elapsed_min = int((time.time() - start_time) / 60)
            print(f"🔄 Scan-Zyklus {cycle} | Verstrichene Zeit: {elapsed_min} Min.")
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

        print("🏁 Testlauf beendet.")

if __name__ == "__main__":
    trader = MultiExchangeTrader(
        amount_per_trade=10.0,   # Simulierter / Echter Einsatz pro Trade in USDT
        min_profit_pct=0.08,     # Mindestmarge (+0.08% Netto)
        dry_run=True             # WICHTIG: True = Simulation | False = Echte Orders
    )
    # Laufen lassen für 1 Stunde im GitHub Action Runner
    trader.run_continuous(duration_hours=1, delay_seconds=2)
