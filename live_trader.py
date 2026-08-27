import csv
import os
import time
import ccxt


class LiveArbitrageTrader:

    def __init__(self, fixed_trade_amount=10.0, min_profit_pct=0.15):
        self.fixed_trade_amount = float(fixed_trade_amount)
        self.min_profit_pct = float(min_profit_pct)
        self.max_raw_margin_pct = 1.5
        self.orderbook_limit = 20

        # Whitelist der Coins (ohne Quote-Asset-Endung)
        self.whitelist_base_assets = {
            "MIN",
            "NES",
            "PRO",
            "USTC",
            "SAND",
            "RVN",
            "PEPE",
            "LUNG",
            "VELO",
            "JASMY",
            "BTC",
            "ETH",
            "SOL",
        }

        # Bevorzugtes Quote-Asset je Börse
        self.preferred_quote = {
            "okx": "USDC",
            "bitrue": "USDT",
            "mexc": "USDT",
        }

        # Spot-Taker-Gebührenstrukturen
        self.exchange_fees = {
            "okx": 0.0010,
            "bitrue": 0.0020,
            "mexc": 0.0010,
        }

        self.csv_file = "live_trading_results_real.csv"
        self.exchanges = {}

        print(
            "🔌 Initialisiere API-Verbindungen für LIVE-Trading (OKX [USDC],"
            " BITRUE [USDT] & MEXC [USDT])..."
        )

        for ex_name, ex_class in [
            ("okx", ccxt.okx),
            ("bitrue", ccxt.bitrue),
            ("mexc", ccxt.mexc),
        ]:
            try:
                api_key = os.getenv(f"{ex_name.upper()}_API_KEY", "")
                secret = os.getenv(f"{ex_name.upper()}_API_SECRET", "")
                password = os.getenv(f"{ex_name.upper()}_PASSPHRASE", "")

                config = {
                    "enableRateLimit": True,
                    "timeout": 8000,
                    "options": {"defaultType": "spot"},
                    "apiKey": api_key,
                    "secret": secret,
                }

                if password:
                    config["password"] = password

                if ex_name == "okx":
                    config["hostname"] = "eea.okx.com"

                instance = ex_class(config)
                fee = self.exchange_fees.get(ex_name, 0.0020)
                self.exchanges[ex_name] = {
                    "instance": instance,
                    "fee": fee,
                }
                print(f"✅ {ex_name.upper()} API erfolgreich verbunden.")
            except Exception as e:
                print(f"❌ {ex_name.upper()} Verbindung fehlgeschlagen: {e}")

        self.init_csv()

    def init_csv(self):
        if not os.path.exists(self.csv_file):
            with open(self.csv_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "timestamp",
                        "base_asset",
                        "buy_ex",
                        "sell_ex",
                        "buy_symbol",
                        "sell_symbol",
                        "trade_amount",
                        "buy_price",
                        "sell_price",
                        "profit_usdt",
                        "status",
                    ],
                )
                writer.writeheader()

    def check_live_balance(self, exchange_name, asset):
        try:
            balance_info = self.exchanges[exchange_name][
                "instance"
            ].fetch_balance()
            free_bal = float(balance_info.get(asset, {}).get("free", 0.0))

            # Falls OKX das Guthaben unter 'USD' statt 'USDC' führt:
            if free_bal == 0.0 and exchange_name == "okx" and asset == "USDC":
                free_bal = float(balance_info.get("USD", {}).get("free", 0.0))

            return free_bal
        except Exception as e:
            print(
                f"⚠️ Guthaben-Abfrage für {exchange_name.upper()} ({asset})"
                f" fehlgeschlagen: {e}"
            )
            return 0.0

    def execute_live_arbitrage(
        self,
        base_asset,
        buy_ex_name,
        sell_ex_name,
        ticker_buy,
        ticker_sell,
        buy_symbol,
        sell_symbol,
    ):
        try:
            buy_ex = self.exchanges[buy_ex_name]["instance"]
            sell_ex = self.exchanges[sell_ex_name]["instance"]

            ask_buy = float(ticker_buy.get("ask", 0) or 0)
            bid_sell = float(ticker_sell.get("bid", 0) or 0)
            if ask_buy <= 0 or bid_sell <= 0:
                return

            raw_margin = ((bid_sell - ask_buy) / ask_buy) * 100
            total_fee_pct = (
                self.exchanges[buy_ex_name]["fee"]
                + self.exchanges[sell_ex_name]["fee"]
            ) * 100

            if (
                raw_margin <= 0
                or raw_margin > self.max_raw_margin_pct
                or (raw_margin - total_fee_pct) < self.min_profit_pct
            ):
                return

            # 1. Kauf-Guthaben prüfen (USDC auf OKX / USDT auf Bitrue & MEXC)
            required_quote_asset = self.preferred_quote.get(buy_ex_name, "USDT")
            current_quote_bal = self.check_live_balance(
                buy_ex_name, required_quote_asset
            )

            if current_quote_bal < self.fixed_trade_amount:
                print(
                    f"ℹ️ [{base_asset}] Spread {raw_margin:.2f}%"
                    f" ({buy_ex_name.upper()} ➔ {sell_ex_name.upper()}): Nicht"
                    f" genug {required_quote_asset} auf {buy_ex_name.upper()}"
                    f" (${current_quote_bal:.2f} / ${self.fixed_trade_amount:.2f})"
                )
                return

            # 2. Verkaufs-Guthaben prüfen (Ziel-Token auf der Verkaufs-Börse)
            required_tokens = self.fixed_trade_amount / ask_buy
            current_tokens = self.check_live_balance(sell_ex_name, base_asset)

            if current_tokens < required_tokens:
                print(
                    f"ℹ️ [{base_asset}] Spread {raw_margin:.2f}%"
                    f" ({buy_ex_name.upper()} ➔ {sell_ex_name.upper()}): Nicht"
                    f" genug {base_asset} auf {sell_ex_name.upper()}"
                    f" ({current_tokens:.4f} / {required_tokens:.4f})"
                )
                return

            # 3. Orderbuch-Check
            ob_buy = buy_ex.fetch_order_book(
                buy_symbol, limit=self.orderbook_limit
            )
            ob_sell = sell_ex.fetch_order_book(
                sell_symbol, limit=self.orderbook_limit
            )
            if not ob_buy.get("asks") or not ob_sell.get("bids"):
                return

            best_ask = float(ob_buy["asks"][0][0])
            best_bid = float(ob_sell["bids"][0][0])

            real_margin = ((best_bid - best_ask) / best_ask) * 100
            real_net_pct = real_margin - total_fee_pct

            if (
                real_net_pct < self.min_profit_pct
                or real_margin > self.max_raw_margin_pct
            ):
                return

            quantity = self.fixed_trade_amount / best_ask

            print("\n" + "🚨" * 25)
            print(
                f"⚡ ECHTER LIVE-TRADE EXECUTION: {base_asset} ({buy_symbol} ➔"
                f" {sell_symbol})"
            )
            print(
                f"Kauf auf {buy_ex_name.upper()} @ ${best_ask:.6f} | Verkauf auf"
                f" {sell_ex_name.upper()} @ ${best_bid:.6f}"
            )
            print("🚨" * 25 + "\n")

            # Kauf-Order
            buy_order = buy_ex.create_order(
                symbol=buy_symbol,
                type="limit",
                side="buy",
                amount=quantity,
                price=best_ask,
                params={"timeInForce": "IOC"},
            )

            filled_qty = float(
                buy_order.get("filled", 0.0) or buy_order.get("amount", 0.0)
            )

            if filled_qty <= 0:
                print(
                    f"⚠️ Buy Order auf {buy_ex_name.upper()} wurde nicht"
                    " gefüllt."
                )
                return

            # Verkaufs-Order
            sell_order = sell_ex.create_order(
                symbol=sell_symbol,
                type="limit",
                side="sell",
                amount=filled_qty,
                price=best_bid,
                params={"timeInForce": "IOC"},
            )

            profit_usdt = round(
                (filled_qty * best_ask) * (real_net_pct / 100), 6
            )

            # Protokollierung
            with open(self.csv_file, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "timestamp",
                        "base_asset",
                        "buy_ex",
                        "sell_ex",
                        "buy_symbol",
                        "sell_symbol",
                        "trade_amount",
                        "buy_price",
                        "sell_price",
                        "profit_usdt",
                        "status",
                    ],
                )
                writer.writerow(
                    {
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "base_asset": base_asset,
                        "buy_ex": buy_ex_name.upper(),
                        "sell_ex": sell_ex_name.upper(),
                        "buy_symbol": buy_symbol,
                        "sell_symbol": sell_symbol,
                        "trade_amount": filled_qty * best_ask,
                        "buy_price": best_ask,
                        "sell_price": best_bid,
                        "profit_usdt": profit_usdt,
                        "status": "LIVE_EXECUTED",
                    }
                )

        except Exception as e:
            print(f"❌ FEHLER beim Live-Trade {base_asset}: {e}")

    def run(self, duration_hours=0.5, delay_seconds=3):
        print(f"\n🚀 Live Trading gestartet. Target: ${self.fixed_trade_amount}")
        end_time = time.time() + duration_hours * 3600

        for name, data in self.exchanges.items():
            try:
                data["instance"].load_markets()
            except Exception as e:
                print(f"⚠️ Märkte laden fehlgeschlagen für {name.upper()}: {e}")

        while time.time() < end_time:
            all_tickers = {}
            for name, data in self.exchanges.items():
                try:
                    all_tickers[name] = data["instance"].fetch_tickers()
                except Exception:
                    pass

            active_exchanges = list(all_tickers.keys())

            for i in range(len(active_exchanges)):
                for j in range(len(active_exchanges)):
                    if i == j:
                        continue
                    ex1, ex2 = active_exchanges[i], active_exchanges[j]
                    t1, t2 = all_tickers.get(ex1, {}), all_tickers.get(ex2, {})

                    for base in self.whitelist_base_assets:
                        quote1 = self.preferred_quote.get(ex1, "USDT")
                        quote2 = self.preferred_quote.get(ex2, "USDT")

                        sym1 = f"{base}/{quote1}"
                        sym2 = f"{base}/{quote2}"

                        if sym1 in t1 and sym2 in t2:
                            self.execute_live_arbitrage(
                                base, ex1, ex2, t1[sym1], t2[sym2], sym1, sym2
                            )

            time.sleep(delay_seconds)


if __name__ == "__main__":
    trader = LiveArbitrageTrader(fixed_trade_amount=10.0, min_profit_pct=0.15)
    trader.run(duration_hours=0.5, delay_seconds=3)



    def print_summary(self, start_time):
        elapsed_min = round((time.time() - start_time) / 60, 1)

        total_trades = 0
        successful_trades = 0
        total_profit = 0.0

        if os.path.exists(self.csv_file):
            with open(self.csv_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("status") == "LIVE_EXECUTED":
                        total_trades += 1
                        profit = float(row.get("profit_usdt", 0.0) or 0.0)
                        total_profit += profit
                        if profit > 0:
                            successful_trades += 1

        win_rate = (
            (successful_trades / total_trades * 100) if total_trades > 0 else 0.0
        )

        print("\n" + "=" * 50)
        print("📊 LIVE TRADING SESSION SUMMARY")
        print("=" * 50)
        print(f"⏱️ Laufzeit: {elapsed_min} Minuten")
        print(f"⚡ Ausgeführte Trades: {total_trades}")
        print(f"💰 Gesamter Reingewinn: +{total_profit:.6f} USDT/USDC")
        print(f"📈 Win Rate: {win_rate:.1f}%")
        print("=" * 50 + "\n")

    def run(self, duration_hours=0.5, delay_seconds=3):
        start_time = time.time()
        print(f"\n🚀 Live Trading gestartet. Target: ${self.fixed_trade_amount}")
        end_time = start_time + duration_hours * 3600

        for name, data in self.exchanges.items():
            try:
                data["instance"].load_markets()
            except Exception as e:
                print(f"⚠️ Märkte laden fehlgeschlagen für {name.upper()}: {e}")

        while time.time() < end_time:
            all_tickers = {}
            for name, data in self.exchanges.items():
                try:
                    all_tickers[name] = data["instance"].fetch_tickers()
                except Exception:
                    pass

            active_exchanges = list(all_tickers.keys())

            for i in range(len(active_exchanges)):
                for j in range(len(active_exchanges)):
                    if i == j:
                        continue
                    ex1, ex2 = active_exchanges[i], active_exchanges[j]
                    t1, t2 = all_tickers.get(ex1, {}), all_tickers.get(ex2, {})

                    for base in self.whitelist_base_assets:
                        quote1 = self.preferred_quote.get(ex1, "USDT")
                        quote2 = self.preferred_quote.get(ex2, "USDT")

                        sym1 = f"{base}/{quote1}"
                        sym2 = f"{base}/{quote2}"

                        if sym1 in t1 and sym2 in t2:
                            self.execute_live_arbitrage(
                                base, ex1, ex2, t1[sym1], t2[sym2], sym1, sym2
                            )

            time.sleep(delay_seconds)

        # Zusammenfassung am Ende des Durchlaufs ausgeben
        self.print_summary(start_time)
