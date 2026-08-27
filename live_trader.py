import os
import time
import csv
import ccxt


class LiveArbitrageTrader:
    def __init__(self, fixed_trade_amount=10.0, min_profit_pct=0.15):
        self.fixed_trade_amount = float(fixed_trade_amount)  # Max $10 pro Trade für Echthandels-Tests
        self.min_profit_pct = float(min_profit_pct)  # Sicherheits-Puffer für Gebühren & Slippage
        self.max_raw_margin_pct = 1.5  # Strikte Obergrenze gegen illiquide Ausreißer
        self.orderbook_limit = 20

        # 🎯 Whitelist der lukrativsten Paare
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
            # Fallback für OKX USD-Notierungen
            "MIN/USD",
            "NES/USD",
            "PRO/USD",
            "USTC/USD",
            "SAND/USD",
            "RVN/USD",
            "PEPE/USD",
            "LUNG/USD",
            "VELO/USD",
            "JASMY/USD",
        }

        # Spot-Taker-Gebührenstrukturen (VIP 0 Standard)
        self.exchange_fees = {
            "okx": 0.0010,
            "kucoin": 0.0010,
            "bitrue": 0.0020,
        }

        self.csv_file = "live_trading_results_real.csv"
        self.exchanges = {}

        print("🔌 Initialisiere API-Verbindungen für LIVE-Trading...")
        for ex_name, ex_class in [
            ("okx", ccxt.okx),
            ("kucoin", ccxt.kucoin),
            ("bitrue", ccxt.bitrue),
        ]:
            try:
                config = {
                    "enableRateLimit": True,
                    "timeout": 10000,
                    "options": {"defaultType": "spot"},
                    "apiKey": os.getenv(f"{ex_name.upper()}_API_KEY", ""),
                    "secret": os.getenv(f"{ex_name.upper()}_API_SECRET", ""),
                }
                passphrase = os.getenv(f"{ex_name.upper()}_PASSPHRASE", "")
                if passphrase:
                    config["password"] = passphrase

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

    def check_live_balance(self, exchange_name):
        """Liest sowohl USDT als auch USD (falls OKX das Guthaben als USD führt)"""
        try:
            balance_info = self.exchanges[exchange_name]["instance"].fetch_balance()
            usdt_free = float(balance_info.get("USDT", {}).get("free", 0.0))
            usd_free = float(balance_info.get("USD", {}).get("free", 0.0))

            total_available = max(usdt_free, usd_free)
            return total_available
        except Exception as e:
            print(f"⚠️ Guthaben-Abfrage für {exchange_name.upper()} fehlgeschlagen: {e}")
            return 0.0

    def execute_live_arbitrage(
        self, symbol, buy_ex_name, sell_ex_name, ticker_buy, ticker_sell
    ):
        try:
            buy_ex = self.exchanges[buy_ex_name]["instance"]
            sell_ex = self.exchanges[sell_ex_name]["instance"]

            # 1. Ticker-Vorprüfung
            ask_buy = float(ticker_buy.get("ask", 0))
            bid_sell = float(ticker_sell.get("bid", 0))
            if ask_buy <= 0 or bid_sell <= 0:
                return

            raw_margin = ((bid_sell - ask_buy) / ask_buy) * 100
            if raw_margin <= 0 or raw_margin > self.max_raw_margin_pct:
                return

            total_fee_pct = (
                self.exchanges[buy_ex_name]["fee"] + self.exchanges[sell_ex_name]["fee"]
            ) * 100
            if (raw_margin - total_fee_pct) < self.min_profit_pct:
                return

            # 2. Echtzeit-Guthaben auf Kauf-Börse prüfen (USDT / USD)
            current_usdt = self.check_live_balance(buy_ex_name)
            if current_usdt < self.fixed_trade_amount:
                print(
                    f"⚠️ [{symbol}] Nicht genug USDT/USD auf {buy_ex_name.upper()} "
                    f"(${current_usdt:.2f} < ${self.fixed_trade_amount:.2f})"
                )
                return

            # 3. Orderbuch prüfen
            ob_buy = buy_ex.fetch_order_book(symbol, limit=self.orderbook_limit)
            ob_sell = sell_ex.fetch_order_book(symbol, limit=self.orderbook_limit)
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

            # 4. Order-Größe berechnen
            quantity = self.fixed_trade_amount / best_ask

            print("\n" + "🚨" * 25)
            print(f"⚡ ECHTER LIVE-TRADE AUSGEFÜHRT! {symbol}")
            print(
                f"Kauf auf {buy_ex_name.upper()} @ ${best_ask:.6f} | "
                f"Verkauf auf {sell_ex_name.upper()} @ ${best_bid:.6f}"
            )
            print(
                f"Einsatz: ${self.fixed_trade_amount:.2f} | Erwartetes Netto: +{real_net_pct:.3f}%"
            )
            print("🚨" * 25 + "\n")

            # 5. EXECUTION: Echte Orders absetzen (IOC Limit-Orders)
            buy_order = buy_ex.create_order(
                symbol=symbol,
                type="limit",
                side="buy",
                amount=quantity,
                price=best_ask,
                params={"timeInForce": "IOC"},
            )
            print(f"✅ BUY Order Platziert: ID {buy_order.get('id', 'N/A')}")

            # Minimaler Puffer für Netzwerk-Synchronisation
            time.sleep(0.15)

            sell_order = sell_ex.create_order(
                symbol=symbol,
                type="limit",
                side="sell",
                amount=quantity,
                price=best_bid,
                params={"timeInForce": "IOC"},
            )
            print(f"✅ SELL Order Platziert: ID {sell_order.get('id', 'N/A')}")

            # Protokollierung
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
                        "trade_amount": self.fixed_trade_amount,
                        "buy_price": best_ask,
                        "sell_price": best_bid,
                        "profit_usdt": round(
                            self.fixed_trade_amount * (real_net_pct / 100), 6
                        ),
                        "status": "LIVE_EXECUTED",
                    }
                )

        except Exception as e:
            print(f"❌ FEHLER beim Live-Trade {symbol}: {e}")

    def run(self, duration_hours=0.5, delay_seconds=3):
        print(
            f"\n🚀 Live Trading gestartet. Festbetrag pro Trade: ${self.fixed_trade_amount:.2f}"
        )
        start_time = time.time()
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

                    t1, t2 = all_tickers[ex1], all_tickers[ex2]

                    # Erkennt /USDT und /USD Handelspaare
                    s1 = {s for s in t1.keys() if s.endswith("/USDT") or s.endswith("/USD")}
                    s2 = {s for s in t2.keys() if s.endswith("/USDT") or s.endswith("/USD")}

                    common_symbols = s1.intersection(s2).intersection(self.whitelist)

                    for symbol in common_symbols:
                        self.execute_live_arbitrage(
                            symbol, ex1, ex2, t1[symbol], t2[symbol]
                        )

            time.sleep(delay_seconds)


if __name__ == "__main__":
    # Startet mit $10.00 maximalem Einsatz pro Trade für 30 Minuten
    trader = LiveArbitrageTrader(fixed_trade_amount=10.0, min_profit_pct=0.15)
    trader.run(duration_hours=0.5, delay_seconds=3)
