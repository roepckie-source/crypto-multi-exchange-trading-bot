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

        # 🎯 Whitelist der Paare (OKX, BITRUE & MEXC)
        self.whitelist = {
            "MIN/USDT",
            "NES/USDT",
            "PRO/USDT",
            "USTC/USDT",
            "SAND/USDT",
            "RVN/USDT",
            "PEPE/USDT",
            "LUNG/USDT",
            "VELO/USDT",
            "JASMY/USDT",
        }

        # Spot-Taker-Gebührenstrukturen
        self.exchange_fees = {
            "okx": 0.0010,
            "bitrue": 0.0020,
            "mexc": 0.0010,  # Standard MEXC Spot-Taker-Gebühr
        }

        self.csv_file = "live_trading_results_real.csv"
        self.exchanges = {}

        print(
            "🔌 Initialisiere API-Verbindungen für LIVE-Trading (OKX, BITRUE &"
            " MEXC)..."
        )

        for ex_name, ex_class in [
            ("okx", ccxt.okx),
            ("bitrue", ccxt.bitrue),
            ("mexc", ccxt.mexc),  # 🚀 MEXC hinzugefügt
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
                        "symbol",
                        "buy_ex",
                        "sell_ex",
                        "trade_amount",
                        "buy_price",
                        "sell_price",
                        "profit_usdt",
                        "status",
                    ],
                )
                writer.writeheader()

    def check_live_balance(self, exchange_name, asset="USDT"):
        try:
            balance_info = self.exchanges[exchange_name][
                "instance"
            ].fetch_balance()
            return float(balance_info.get(asset, {}).get("free", 0.0))
        except Exception as e:
            print(
                f"⚠️ Guthaben-Abfrage für {exchange_name.upper()} ({asset})"
                f" fehlgeschlagen: {e}"
            )
            return 0.0

    def execute_live_arbitrage(
        self, symbol, buy_ex_name, sell_ex_name, ticker_buy, ticker_sell
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

            current_usdt = self.check_live_balance(buy_ex_name, "USDT")
            if current_usdt < self.fixed_trade_amount:
                return

            ob_buy = buy_ex.fetch_order_book(symbol, limit=self.orderbook_limit)
            ob_sell = sell_ex.fetch_order_book(
                symbol, limit=self.orderbook_limit
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
            print(f"⚡ ECHTER LIVE-TRADE EXECUTION: {symbol}")
            print(
                f"Kauf auf {buy_ex_name.upper()} @ ${best_ask:.6f} | Verkauf auf"
                f" {sell_ex_name.upper()} @ ${best_bid:.6f}"
            )
            print("🚨" * 25 + "\n")

            buy_order = buy_ex.create_order(
                symbol=symbol,
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
                    " gefüllt (IOC Storniert)."
                )
                return

            sell_order = sell_ex.create_order(
                symbol=symbol,
                type="limit",
                side="sell",
                amount=filled_qty,
                price=best_bid,
                params={"timeInForce": "IOC"},
            )

            with open(self.csv_file, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "timestamp",
                        "symbol",
                        "buy_ex",
                        "sell_ex",
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
                        "symbol": symbol,
                        "buy_ex": buy_ex_name.upper(),
                        "sell_ex": sell_ex_name.upper(),
                        "trade_amount": filled_qty * best_ask,
                        "buy_price": best_ask,
                        "sell_price": best_bid,
                        "profit_usdt": round(
                            (filled_qty * best_ask) * (real_net_pct / 100), 6
                        ),
                        "status": "LIVE_EXECUTED",
                    }
                )

        except Exception as e:
            print(f"❌ FEHLER beim Live-Trade {symbol}: {e}")

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

                    s1 = set(t1.keys())
                    s2 = set(t2.keys())

                    common_symbols = s1.intersection(s2).intersection(
                        self.whitelist
                    )

                    for symbol in common_symbols:
                        self.execute_live_arbitrage(
                            symbol, ex1, ex2, t1[symbol], t2[symbol]
                        )

            time.sleep(delay_seconds)


if __name__ == "__main__":
    trader = LiveArbitrageTrader(fixed_trade_amount=10.0, min_profit_pct=0.15)
    trader.run(duration_hours=0.5, delay_seconds=3)
