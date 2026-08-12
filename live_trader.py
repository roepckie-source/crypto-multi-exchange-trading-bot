import os
import time
import csv
import ccxt

class LiveTraderDryRun:
    def __init__(self, amount_per_trade=10.0, min_profit_pct=0.10, dry_run=True):
        self.amount = amount_per_trade          # Einsatz pro Trade in USDT
        self.min_profit_pct = min_profit_pct    # Mindestgewinn in % (z.B. 0.10%)
        self.max_profit_pct = 5.0              # Maximal realistischer Gewinn
        self.dry_run = dry_run                  # Safety Toggle: True = Keine echten Orders
        
        self.csv_file = "live_dry_run_results.csv"

        # API-Keys sicher aus GitHub Secrets / System-Umgebung auslesen
        self.exchanges = {
            'mexc': {
                'instance': ccxt.mexc({
                    'apiKey': os.getenv('MEXC_API_KEY', ''),
                    'secret': os.getenv('MEXC_API_SECRET', ''),
                    'enableRateLimit': True,
                }),
                'fee': 0.0005
            },
            'gate': {
                'instance': ccxt.gate({
                    'apiKey': os.getenv('GATE_API_KEY', ''),
                    'secret': os.getenv('GATE_API_SECRET', ''),
                    'enableRateLimit': True,
                }),
                'fee': 0.002
            }
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

    def check_exchange_limits(self, exchange_name, symbol, amount_usdt, price):
        """ Prüft, ob der geplante Trade die Mindestgrenzen der Börse einhält """
        try:
            ex = self.exchanges[exchange_name]['instance']
            market = ex.market(symbol)
            
            # Berechne Coin-Menge
            coin_amount = amount_usdt / price

            # Mindest-Amount in Coins
            min_amount = market.get('limits', {}).get('amount', {}).get('min')
            # Mindest-Auftragswert in USDT (Cost)
            min_cost = market.get('limits', {}).get('cost', {}).get('min')

            if min_amount and coin_amount < min_amount:
                return False, f"Menge zu gering (Min: {min_amount})"
            if min_cost and amount_usdt < min_cost:
                return False, f"Auftragswert zu gering (Min USDT: {min_cost})"

            return True, "OK"
        except Exception as e:
            # Falls Market-Limits nicht geladen werden konnten
            return True, f"Limits nicht prüfbar: {e}"

    def calculate_depth_execution(self, orderbook, amount_needed, is_buy=True):
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
            return None, None
        
        avg_price = total_cost / amount_needed
        return avg_price, filled_amount

    def execute_arbitrage(self, symbol, buy_ex_name, sell_ex_name):
        buy_ex = self.exchanges[buy_ex_name]['instance']
        sell_ex = self.exchanges[sell_ex_name]['instance']

        try:
            ob_buy = buy_ex.fetch_order_book(symbol, limit=10)
            ob_sell = sell_ex.fetch_order_book(symbol, limit=10)

            # 1. Kaufpreis inklusive Slippage im Orderbuch berechnen
            avg_buy_price, _ = self.calculate_depth_execution(ob_buy, self.amount, is_buy=True)
            if not avg_buy_price:
                return

            fee_buy = self.exchanges[buy_ex_name]['fee']
            fee_sell = self.exchanges[sell_ex_name]['fee']

            bought_coins = (self.amount / avg_buy_price) * (1 - fee_buy)

            # 2. Verkaufspreis inklusive Slippage im Orderbuch berechnen
            avg_sell_price, _ = self.calculate_depth_execution(ob_sell, bought_coins, is_buy=False)
            if not avg_sell_price:
                return

            final_usdt = (bought_coins * avg_sell_price) * (1 - fee_sell)
            real_profit_pct = ((final_usdt - self.amount) / self.amount) * 100
            profit_usd = final_usdt - self.amount

            # 3. Kriterien für Tradereife prüfen
            if self.min_profit_pct <= real_profit_pct <= self.max_profit_pct:
                
                # Handels-Limits der Börsen abfragen
                buy_limits_ok, buy_note = self.check_exchange_limits(buy_ex_name, symbol, self.amount, avg_buy_price)
                sell_limits_ok, sell_note = self.check_exchange_limits(sell_ex_name, symbol, final_usdt, avg_sell_price)

                limits_ok = buy_limits_ok and sell_limits_ok
                
                status_text = "EXECUTION_READY" if limits_ok else f"LIMIT_FAILED (Buy: {buy_note} | Sell: {sell_note})"

                if self.dry_run:
                    print(f"🔥 [DRY RUN MATCH] {symbol}: {buy_ex_name.upper()} -> {sell_ex_name.upper()} "
                          f"| Marge: +{real_profit_pct:.3f}% (+${profit_usd:.3f}) | Status: {status_text}")
                else:
                    # HIER FOLGT IN SCHRITT 3 DIE ECHTE ORDERAUSFÜHRUNG
                    # buy_ex.create_limit_buy_order(symbol, bought_coins, avg_buy_price)
                    # sell_ex.create_limit_sell_order(symbol, bought_coins, avg_sell_price)
                    pass

                self.log_trade(symbol, buy_ex_name, sell_ex_name, avg_buy_price, avg_sell_price, 
                               real_profit_pct, profit_usd, limits_ok, status_text)

        except Exception as e:
            # Abfang von Netzwerkfehlern / API-Limits
            pass

    def log_trade(self, symbol, buy_ex, sell_ex, buy_p, sell_p, pct, usd, limits_ok, status):
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
                "buy_price": buy_p,
                "sell_price": sell_p,
                "real_profit_pct": round(pct, 4),
                "profit_usd": round(usd, 4),
                "min_amount_ok": limits_ok,
                "execution_mode": "DRY_RUN" if self.dry_run else "LIVE_REAL",
                "status": status
            })

    def run(self, cycles=10):
        print(f"🚀 Starte LIVE-Trader im [DRY RUN MODUS] (Einsatz: ${self.amount} USD)...")
        
        # Märkte laden, um Limits lokal verfügbar zu haben
        for name, data in self.exchanges.items():
            try:
                data['instance'].load_markets()
            except Exception as e:
                print(f"⚠️ Konnte Märkte für {name} nicht laden: {e}")

        for cycle in range(1, cycles + 1):
            print(f"🔄 Live-Scan Zyklus {cycle}/{cycles}...")
            
            try:
                tickers_mexc = self.exchanges['mexc']['instance'].fetch_tickers()
                tickers_gate = self.exchanges['gate']['instance'].fetch_tickers()

                syms_mexc = {s for s in tickers_mexc.keys() if s.endswith('/USDT')}
                syms_gate = {s for s in tickers_gate.keys() if s.endswith('/USDT')}
                common = list(syms_mexc.intersection(syms_gate))

                for symbol in common:
                    self.execute_arbitrage(symbol, 'mexc', 'gate')
                    self.execute_arbitrage(symbol, 'gate', 'mexc')

            except Exception as e:
                print(f"⚠️ Fehler im Zyklus: {e}")

            time.sleep(1)

if __name__ == "__main__":
    # Trockenlauf mit 10 USDT Einsatz pro Trade (Safety Toggle: dry_run=True)
    trader = LiveTraderDryRun(amount_per_trade=10.0, min_profit_pct=0.10, dry_run=True)
    trader.run(cycles=10)
