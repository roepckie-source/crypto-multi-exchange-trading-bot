import os
import time
import csv
import ccxt

class MultiExchangeTrader:
    def __init__(self, amount_per_trade=10.0, min_profit_pct=0.08, dry_run=True):
        self.amount = amount_per_trade          # Einsatz pro Trade in USDT (z. B. $10)
        self.min_profit_pct = min_profit_pct    # Mindestgewinn in % (z. B. 0.08%)
        self.max_profit_pct = 5.0               # Safety-Cap gegen fehlerhafte Ticker
        self.dry_run = dry_run                  # True = Simulation (Paper Trading) | False = ECHTE ORDERS!
        
        self.csv_file = "paper_trading_results.csv" if dry_run else "live_trading_results.csv"
        self.chancen_csv_file = "log_chancen.csv"  # CSV für knapp verfehlte Chancen
        self.exchanges = {}

        # 1. OKX Setup
        okx_key = os.getenv('OKX_API_KEY', '')
        try:
            okx_config = {
                'enableRateLimit': True,
                'options': {'defaultType': 'spot'}
            }
            if okx_key:
                okx_config.update({
                    'apiKey': okx_key,
                    'secret': os.getenv('OKX_API_SECRET', ''),
                    'password': os.getenv('OKX_PASSPRASE', '')
                })
            ex = ccxt.okx(okx_config)
            ex.hostname = 'my.okx.com'
            self.exchanges['okx'] = {'instance': ex, 'fee': 0.001}
        except Exception as e:
            print(f"⚠️ OKX Initialisierungsfehler: {e}")

        # 2. KuCoin Setup
        kucoin_key = os.getenv('KUCOIN_API_KEY', '')
        try:
            kucoin_config = {'enableRateLimit': True}
            if kucoin_key and not dry_run:
                kucoin_config.update({
                    'apiKey': kucoin_key,
                    'secret': os.getenv('KUCOIN_API_SECRET', ''),
                    'password': os.getenv('KUCOIN_PASSPRASE', '')
                })
            ex = ccxt.kucoin(kucoin_config)
            self.exchanges['kucoin'] = {'instance': ex, 'fee': 0.001}
        except Exception as e:
            print(f"⚠️ KuCoin Initialisierungsfehler: {e}")

        self.init_csv()

    def init_csv(self):
        """ Erstellt die CSV-Logdateien, falls sie nicht existieren """
        if not os.path.exists(self.csv_file):
            with open(self.csv_file, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=[
                    "timestamp", "symbol", "buy_ex", "sell_ex", 
                    "buy_price", "sell_price", "real_profit_pct", 
                    "profit_usd", "execution_mode", "status"
                ])
                writer.writeheader()

        if not os.path.exists(self.chancen_csv_file):
            with open(self.chancen_csv_file, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=[
                    "timestamp", "symbol", "buy_ex", "sell_ex", 
                    "ask_buy", "bid_sell", "raw_margin_pct", 
                    "total_fee_pct", "estimated_net_pct", "reason"
                ])
                writer.writeheader()

    def log_missed_chance(self, symbol, buy_ex_name, sell_ex_name, ask_buy, bid_sell, raw_margin, total_fee_pct, estimated_net, reason):
        """ Protokolliert verfehlte oder knappe Chancen in log_chancen.csv """
        with open(self.chancen_csv_file, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "timestamp", "symbol", "buy_ex", "sell_ex", 
                "ask_buy", "bid_sell", "raw_margin_pct", 
                "total_fee_pct", "estimated_net_pct", "reason"
            ])
            writer.writerow({
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "symbol": symbol,
                "buy_ex": buy_ex_name.upper(),
                "sell_ex": sell_ex_name.upper(),
                "ask_buy": ask_buy,
                "bid_sell": bid_sell,
                "raw_margin_pct": round(raw_margin, 4),
                "total_fee_pct": round(total_fee_pct, 4),
                "estimated_net_pct": round(estimated_net, 4),
                "reason": reason
            })

    def execute_arbitrage(self, symbol, buy_ex_name, sell_ex_name, ticker_buy, ticker_sell):
        bid_sell = ticker_sell.get('bid')
        ask_buy = ticker_buy.get('ask')

        if not bid_sell or not ask_buy or ask_buy == 0:
            return

        # 1. Brutto-Marge berechnen
        raw_margin = ((bid_sell - ask_buy) / ask_buy) * 100

        # Geschätzte Gesamtgebühr beider Börsen
        fee_buy = self.exchanges[buy_ex_name]['fee']
        fee_sell = self.exchanges[sell_ex_name]['fee']
        total_fee_pct = (fee_buy + fee_sell) * 100
        estimated_net = raw_margin - total_fee_pct

        # Console-Log & CSV-Speicherung für knappe Chancen (ab Brutto > 0.05%)
        if raw_margin >= 0.05:
            print(f"👀 [CHANCE ENTDECKT] {symbol} ({buy_ex_name.upper()} -> {sell_ex_name.upper()}): "
                  f"Brutto: +{raw_margin:.3f}% | Est. Netto: {estimated_net:+.3f}%")

            if estimated_net < self.min_profit_pct:
                self.log_missed_chance(
                    symbol, buy_ex_name, sell_ex_name, 
                    ask_buy, bid_sell, raw_margin, 
                    total_fee_pct, estimated_net, "BELOW_MIN_PROFIT"
                )

        if estimated_net < self.min_profit_pct:
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

            # Liquiditätsprüfung
            buy_volume_available = ob_buy['asks'][0][1] * buy_price
            if buy_volume_available < self.amount:
                print(f"⚠️ [{symbol}] Verworfen: Orderbuch-Liquidität zu gering (${buy_volume_available:.2f} < ${self.amount})")
                self.log_missed_chance(
                    symbol, buy_ex_name, sell_ex_name, 
                    buy_price, sell_price, raw_margin, 
                    total_fee_pct, estimated_net, "LOW_LIQUIDITY"
                )
                return

            # Exakte Netto-Berechnung
            bought_coins = (self.amount / buy_price) * (1 - fee_buy)
            final_usdt = (bought_coins * sell_price) * (1 - fee_sell)
            
            real_profit_pct = ((final_usdt - self.amount) / self.amount) * 100
            profit_usd = final_usdt - self.amount

            if self.min_profit_pct <= real_profit_pct <= self.max_profit_pct:
                mode_str = "PAPER_TRADING" if self.dry_run else "LIVE_REAL_MONEY"
                print(f"🔥 [{mode_str}] {symbol}: {buy_ex_name.upper()} -> {sell_ex_name.upper()} "
                      f"| Marge: +{real_profit_pct:.3f}% (+${profit_usd:.4f})")

                status = "SIMULATED_READY"

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

        except Exception:
            pass

    def run_continuous(self, duration_hours=1, delay_seconds=2):
        mode_label = "PAPER TRADING (SIMULATION)" if self.dry_run else "LIVE TRADING (ECHTGELD)"
        print(f"🚀 Starte Trader [{mode_label}]...")
        print(f"⏱️ Laufzeit: {duration_hours} Stunde(n) | Pause zwischen Scans: {delay_seconds}s")
        
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
        amount_per_trade=10.0,
        min_profit_pct=0.08,
        dry_run=True
    )
    trader.run_continuous(duration_hours=1, delay_seconds=2)
