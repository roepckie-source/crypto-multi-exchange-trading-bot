import os
import time
import csv
import ccxt

class MultiExchangeLiveTrader:
    def __init__(self, amount_per_trade=10.0, min_profit_pct=0.10, dry_run=True):
        self.amount = amount_per_trade          # Einsatz pro Trade in USDT
        self.min_profit_pct = min_profit_pct    # Mindestgewinn in %
        self.max_profit_pct = 5.0              # Safety-Cap gegen Ausreißer/Fake-Daten
        self.dry_run = dry_run                  # Safety Toggle: True = Dry Run
        
        self.csv_file = "live_dry_run_results.csv"

        # Dynamische Einbindung von OKX, KuCoin und MEXC
        self.exchanges = {}

        # 1. OKX Setup
        okx_key = os.getenv('OKX_API_KEY', '')
        if okx_key:
            self.exchanges['okx'] = {
                'instance': ccxt.okx({
                    'apiKey': okx_key,
                    'secret': os.getenv('OKX_API_SECRET', ''),
                    'password': os.getenv('OKX_PASSPRASE', ''),
                    'enableRateLimit': True,
                }),
                'fee': 0.001
            }

        # 2. KuCoin Setup
        kucoin_key = os.getenv('KUCOIN_API_KEY', '')
        if kucoin_key:
            self.exchanges['kucoin'] = {
                'instance': ccxt.kucoin({
                    'apiKey': kucoin_key,
                    'secret': os.getenv('KUCOIN_API_SECRET', ''),
                    'password': os.getenv('KUCOIN_PASSPRASE', ''),
                    'enableRateLimit': True,
                }),
                'fee': 0.001
            }

        # 3. MEXC Setup
        mexc_key = os.getenv('MEXC_API_KEY', '')
        if mexc_key:
            self.exchanges['mexc'] = {
                'instance': ccxt.mexc({
                    'apiKey': mexc_key,
                    'secret': os.getenv('MEXC_API_SECRET', ''),
                    'enableRateLimit': True,
                }),
                'fee': 0.0005
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
        """ Prüft Mindestauftragswerte der jeweiligen Börse """
        try:
            ex = self.exchanges[exchange_name]['instance']
            market = ex.market(symbol)
            coin_amount = amount_usdt / price

            min_amount = market.get('limits', {}).get('amount', {}).get('min')
            min_cost = market.get('limits', {}).get('cost', {}).get('min')

            if min_amount and coin_amount < min_amount:
                return False, f"Menge zu gering (Min: {min_amount})"
            if min_cost and amount_usdt < min_cost:
                return False, f"Auftragswert zu gering (Min USDT: {min_cost})"

            return True, "OK"
        except Exception as e:
            return True, f"Limits-Check übersprungen: {e}"

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

            avg_buy_price, _ = self.calculate_depth_execution(ob_buy, self.amount, is_buy=True)
            if not avg_buy_price:
                return

            fee_buy = self.exchanges[buy_ex_name]['fee']
            fee_sell = self.exchanges[sell_ex_name]['fee']

            bought_coins = (self.amount / avg_buy_price) * (1 - fee_buy)

            avg_sell_price, _ = self.calculate_depth_execution(ob_sell, bought_coins, is_buy=False)
            if not avg_sell_price:
                return

            final_usdt = (bought_coins * avg_sell_price) * (1 - fee_sell)
            real_profit_pct = ((final_usdt - self.amount) / self.amount) * 100
            profit_usd = final_usdt - self.amount

            if self.min_profit_pct <= real_profit_pct <= self.max_profit_pct:
                buy_limits_ok, buy_note = self.check_exchange_limits(buy_ex_name, symbol, self.amount, avg_buy_price)
                sell_limits_ok, sell_note = self.check_exchange_limits(sell_ex_name, symbol, final_usdt, avg_sell_price)

                limits_ok = buy_limits_ok and sell_limits_ok
                status_text = "EXECUTION_READY" if limits_ok else f"LIMIT_FAILED (Buy: {buy_note} | Sell: {sell_note})"

                print(f"🔥 [DRY RUN] {symbol}: {buy_ex_name.upper()} -> {sell_ex_name.upper()} "
                      f"| Marge: +{real_profit_pct:.3f}% (+${profit_usd:.3f}) | Status: {status_text}")

                self.log_trade(symbol, buy_ex_name, sell_ex_name, avg_buy_price, avg_sell_price, 
                               real_profit_pct, profit_usd, limits_ok, status_text)

        except Exception:
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
        active_names = list(self.exchanges.keys())
        print(f"🚀 Starte LIVE-Trader [DRY RUN] über Börsen: {', '.join([n.upper() for n in active_names])}...")
        
        for name, data in self.exchanges.items():
            try:
                data['instance'].load_markets()
            except Exception as e:
                print(f"⚠️ Konnte Märkte für {name} nicht laden: {e}")

        for cycle in range(1, cycles + 1):
            print(f"🔄 Scan-Zyklus {cycle}/{cycles}...")
            
            # Alle Kombinationen vergleichen
            for i in range(len(active_names)):
                for j in range(len(active_names)):
                    if i != j:
                        ex1, ex2 = active_names[i], active_names[j]
                        try:
                            t1 = self.exchanges[ex1]['instance'].fetch_tickers()
                            t2 = self.exchanges[ex2]['instance'].fetch_tickers()

                            s1 = {s for s in t1.keys() if s.endswith('/USDT')}
                            s2 = {s for s in t2.keys() if s.endswith('/USDT')}
                            common = list(s1.intersection(s2))

                            for symbol in common:
                                self.execute_arbitrage(symbol, ex1, ex2)
                        except Exception as e:
                            print(f"⚠️ Fehler beim Pair-Fetch {ex1}-{ex2}: {e}")

            time.sleep(1)

if __name__ == "__main__":
    trader = MultiExchangeLiveTrader(amount_per_trade=10.0, min_profit_pct=0.10, dry_run=True)
    trader.run(cycles=5)
