import os
import time
import csv
import ccxt


class MultiExchangeTrader:

    def __init__(
        self,
        amount_per_trade=10.0,
        starting_balance=1000.0,
        min_profit_pct=0.10,
        dry_run=True
    ):

        # =====================================================
        # GRUNDEINSTELLUNGEN
        # =====================================================

        self.amount = float(amount_per_trade)
        self.starting_balance = float(starting_balance)
        self.paper_balance = float(starting_balance)

        self.min_profit_pct = float(min_profit_pct)

        # Sicherheitsgrenzen
        self.max_raw_margin_pct = 5.0

        # Paper Trading
        self.dry_run = dry_run

        # Orderbook
        self.orderbook_limit = 20

        # Scan
        self.delay_seconds = 2

        # =====================================================
        # STATISTIK
        # =====================================================

        self.total_trades = 0
        self.profitable_trades = 0
        self.total_profit = 0.0

        self.best_trade_profit = 0.0
        self.worst_trade_profit = 0.0

        # Bereits gehandelte Chancen
        # verhindert Doppelzählung derselben Chance
        self.recent_trades = {}

        # Cooldown in Sekunden
        self.trade_cooldown = 30

        # =====================================================
        # CSV
        # =====================================================

        self.csv_file = (
            "paper_trading_results.csv"
            if dry_run
            else "live_trading_results.csv"
        )

        self.chancen_csv_file = "log_chancen.csv"

        self.exchanges = {}

        # =====================================================
        # OKX
        # =====================================================

        try:

            okx_config = {
                "enableRateLimit": True,
                "timeout": 10000,
                "options": {
                    "defaultType": "spot"
                }
            }

            okx_key = os.getenv(
                "OKX_API_KEY",
                ""
            )

            if okx_key and not dry_run:

                okx_config.update({
                    "apiKey": okx_key,
                    "secret": os.getenv(
                        "OKX_API_SECRET",
                        ""
                    ),
                    "password": os.getenv(
                        "OKX_PASSPRASE",
                        ""
                    )
                })

            ex = ccxt.okx(okx_config)

            self.exchanges["okx"] = {
                "instance": ex,
                "fee": 0.001
            }

        except Exception as e:

            print(
                f"⚠️ OKX Initialisierungsfehler: {e}"
            )

        # =====================================================
        # KUCOIN
        # =====================================================

        try:

            kucoin_config = {
                "enableRateLimit": True,
                "timeout": 10000
            }

            kucoin_key = os.getenv(
                "KUCOIN_API_KEY",
                ""
            )

            if kucoin_key and not dry_run:

                kucoin_config.update({
                    "apiKey": kucoin_key,
                    "secret": os.getenv(
                        "KUCOIN_API_SECRET",
                        ""
                    ),
                    "password": os.getenv(
                        "KUCOIN_PASSPRASE",
                        ""
                    )
                })

            ex = ccxt.kucoin(kucoin_config)

            self.exchanges["kucoin"] = {
                "instance": ex,
                "fee": 0.001
            }

        except Exception as e:

            print(
                f"⚠️ KuCoin Initialisierungsfehler: {e}"
            )

        self.init_csv()

    # =========================================================
    # CSV INITIALISIEREN
    # =========================================================

    def init_csv(self):

        if not os.path.exists(self.csv_file):

            with open(
                self.csv_file,
                "w",
                newline="",
                encoding="utf-8"
            ) as f:

                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "timestamp",
                        "symbol",
                        "buy_ex",
                        "sell_ex",
                        "buy_price",
                        "sell_price",
                        "raw_margin_pct",
                        "real_profit_pct",
                        "profit_usd",
                        "paper_balance",
                        "execution_mode",
                        "status"
                    ]
                )

                writer.writeheader()

        if not os.path.exists(
            self.chancen_csv_file
        ):

            with open(
                self.chancen_csv_file,
                "w",
                newline="",
                encoding="utf-8"
            ) as f:

                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "timestamp",
                        "symbol",
                        "buy_ex",
                        "sell_ex",
                        "ask_buy",
                        "bid_sell",
                        "raw_margin_pct",
                        "estimated_net_pct",
                        "reason"
                    ]
                )

                writer.writeheader()

    # =========================================================
    # CHANCE LOG
    # =========================================================

    def log_chance(
        self,
        symbol,
        buy_ex,
        sell_ex,
        ask_buy,
        bid_sell,
        raw_margin,
        estimated_net,
        reason
    ):

        try:

            with open(
                self.chancen_csv_file,
                "a",
                newline="",
                encoding="utf-8"
            ) as f:

                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "timestamp",
                        "symbol",
                        "buy_ex",
                        "sell_ex",
                        "ask_buy",
                        "bid_sell",
                        "raw_margin_pct",
                        "estimated_net_pct",
                        "reason"
                    ]
                )

                writer.writerow({
                    "timestamp":
                        time.strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),

                    "symbol":
                        symbol,

                    "buy_ex":
                        buy_ex.upper(),

                    "sell_ex":
                        sell_ex.upper(),

                    "ask_buy":
                        ask_buy,

                    "bid_sell":
                        bid_sell,

                    "raw_margin_pct":
                        round(
                            raw_margin,
                            4
                        ),

                    "estimated_net_pct":
                        round(
                            estimated_net,
                            4
                        ),

                    "reason":
                        reason
                })

        except Exception as e:

            print(
                f"⚠️ CSV-Fehler: {e}"
            )

    # =========================================================
    # DUPLIKAT-SCHUTZ
    # =========================================================

    def is_duplicate_trade(
        self,
        symbol,
        buy_ex,
        sell_ex
    ):

        key = (
            f"{symbol}|"
            f"{buy_ex}|"
            f"{sell_ex}"
        )

        now = time.time()

        last_time = self.recent_trades.get(
            key,
            0
        )

        if (
            now - last_time
            < self.trade_cooldown
        ):

            return True

        self.recent_trades[key] = now

        return False

    # =========================================================
    # BUY ORDERBOOK
    # =========================================================

    def simulate_buy(
        self,
        asks,
        usdt_amount
    ):

        remaining_usdt = usdt_amount
        coin_amount = 0.0
        spent_usdt = 0.0

        for level in asks:

            if len(level) < 2:
                continue

            price = float(level[0])
            quantity = float(level[1])

            if price <= 0 or quantity <= 0:
                continue

            level_value = (
                price * quantity
            )

            if (
                level_value
                <= remaining_usdt
            ):

                buy_quantity = quantity

            else:

                buy_quantity = (
                    remaining_usdt
                    / price
                )

            cost = (
                buy_quantity
                * price
            )

            coin_amount += buy_quantity
            spent_usdt += cost
            remaining_usdt -= cost

            if remaining_usdt <= 0.00000001:
                break

        if (
            spent_usdt
            < usdt_amount * 0.999
        ):

            return None

        if coin_amount <= 0:
            return None

        return {
            "coin_amount":
                coin_amount,

            "spent_usdt":
                spent_usdt,

            "average_price":
                spent_usdt
                / coin_amount
        }

    # =========================================================
    # SELL ORDERBOOK
    # =========================================================

    def simulate_sell(
        self,
        bids,
        coin_amount
    ):

        remaining_coin = coin_amount
        received_usdt = 0.0
        sold_coin = 0.0

        for level in bids:

            if len(level) < 2:
                continue

            price = float(level[0])
            quantity = float(level[1])

            if price <= 0 or quantity <= 0:
                continue

            sell_quantity = min(
                remaining_coin,
                quantity
            )

            received_usdt += (
                sell_quantity
                * price
            )

            sold_coin += sell_quantity

            remaining_coin -= (
                sell_quantity
            )

            if (
                remaining_coin
                <= 0.00000001
            ):

                break

        if (
            sold_coin
            < coin_amount * 0.999
        ):

            return None

        if sold_coin <= 0:
            return None

        return {
            "received_usdt":
                received_usdt,

            "average_price":
                received_usdt
                / sold_coin
        }

    # =========================================================
    # ARBITRAGE
    # =========================================================

    def execute_arbitrage(
        self,
        symbol,
        buy_ex_name,
        sell_ex_name,
        ticker_buy,
        ticker_sell
    ):

        try:

            ask_buy = ticker_buy.get(
                "ask"
            )

            bid_sell = ticker_sell.get(
                "bid"
            )

            if not ask_buy or not bid_sell:
                return

            ask_buy = float(
                ask_buy
            )

            bid_sell = float(
                bid_sell
            )

            if (
                ask_buy <= 0
                or bid_sell <= 0
            ):
                return

            # -------------------------------------------------
            # TICKER MARGE
            # -------------------------------------------------

            raw_margin = (
                (
                    bid_sell
                    - ask_buy
                )
                / ask_buy
            ) * 100

            if raw_margin <= 0:
                return

            # -------------------------------------------------
            # XTER-SCHUTZ
            # -------------------------------------------------

            if (
                raw_margin
                > self.max_raw_margin_pct
            ):

                print(
                    f"🛑 [{symbol}] "
                    f"Ungültige Preisdifferenz "
                    f"+{raw_margin:.3f}% "
                    f"→ VERWORFEN"
                )

                self.log_chance(
                    symbol,
                    buy_ex_name,
                    sell_ex_name,
                    ask_buy,
                    bid_sell,
                    raw_margin,
                    0,
                    "INVALID_SPREAD"
                )

                return

            # -------------------------------------------------
            # GEBÜHREN
            # -------------------------------------------------

            fee_buy = self.exchanges[
                buy_ex_name
            ]["fee"]

            fee_sell = self.exchanges[
                sell_ex_name
            ]["fee"]

            total_fee_pct = (
                fee_buy
                + fee_sell
            ) * 100

            estimated_net = (
                raw_margin
                - total_fee_pct
            )

            if raw_margin >= 0.05:

                print(
                    f"👀 {symbol} "
                    f"({buy_ex_name.upper()} "
                    f"-> "
                    f"{sell_ex_name.upper()}): "
                    f"Ticker-Brutto "
                    f"+{raw_margin:.3f}% | "
                    f"geschätzt Netto "
                    f"{estimated_net:+.3f}%"
                )

            # -------------------------------------------------
            # MINDESTGEWINN
            # -------------------------------------------------

            if (
                estimated_net
                < self.min_profit_pct
            ):

                return

            # -------------------------------------------------
            # KAPITALPRÜFUNG
            # -------------------------------------------------

            if self.dry_run:

                if (
                    self.paper_balance
                    < self.amount
                ):

                    print(
                        "⚠️ Nicht genügend "
                        "Paper-Kapital."
                    )

                    return

            # -------------------------------------------------
            # DUPLIKAT-SCHUTZ
            # -------------------------------------------------

            if self.is_duplicate_trade(
                symbol,
                buy_ex_name,
                sell_ex_name
            ):

                return

            # -------------------------------------------------
            # ORDERBOOK
            # -------------------------------------------------

            buy_ex = self.exchanges[
                buy_ex_name
            ]["instance"]

            sell_ex = self.exchanges[
                sell_ex_name
            ]["instance"]

            ob_buy = (
                buy_ex.fetch_order_book(
                    symbol,
                    limit=self.orderbook_limit
                )
            )

            ob_sell = (
                sell_ex.fetch_order_book(
                    symbol,
                    limit=self.orderbook_limit
                )
            )

            if (
                not ob_buy.get("asks")
                or not ob_sell.get("bids")
            ):

                return

            real_buy_price = float(
                ob_buy["asks"][0][0]
            )

            real_sell_price = float(
                ob_sell["bids"][0][0]
            )

            # -------------------------------------------------
            # ORDERBOOK MARGE
            # -------------------------------------------------

            real_raw_margin = (
                (
                    real_sell_price
                    - real_buy_price
                )
                / real_buy_price
            ) * 100

            if (
                real_raw_margin <= 0
                or
                real_raw_margin
                > self.max_raw_margin_pct
            ):

                return

            # -------------------------------------------------
            # BUY SIMULATION
            # -------------------------------------------------

            buy_result = (
                self.simulate_buy(
                    ob_buy["asks"],
                    self.amount
                )
            )

            if not buy_result:

                return

            coin_amount = (
                buy_result["coin_amount"]
                * (1 - fee_buy)
            )

            # -------------------------------------------------
            # SELL SIMULATION
            # -------------------------------------------------

            sell_result = (
                self.simulate_sell(
                    ob_sell["bids"],
                    coin_amount
                )
            )

            if not sell_result:

                return

            final_usdt = (
                sell_result[
                    "received_usdt"
                ]
                * (1 - fee_sell)
            )

            # -------------------------------------------------
            # NETTO
            # -------------------------------------------------

            profit_usdt = (
                final_usdt
                - self.amount
            )

            real_profit_pct = (
                profit_usdt
                / self.amount
            ) * 100

            # -------------------------------------------------
            # SICHERHEIT
            # -------------------------------------------------

            if (
                real_profit_pct
                > self.max_raw_margin_pct
            ):

                print(
                    f"🛑 [{symbol}] "
                    f"Unplausibler Gewinn "
                    f"+{real_profit_pct:.3f}% "
                    f"→ VERWORFEN"
                )

                return

            if (
                real_profit_pct
                < self.min_profit_pct
            ):

                return

            # =================================================
            # PAPER TRADE
            # =================================================

            mode_str = (
                "PAPER_TRADING"
                if self.dry_run
                else "LIVE_REAL_MONEY"
            )

            # Kapital aktualisieren
            if self.dry_run:

                self.paper_balance += (
                    profit_usdt
                )

            self.total_trades += 1

            self.total_profit += (
                profit_usdt
            )

            if profit_usdt > 0:

                self.profitable_trades += 1

            if (
                profit_usdt
                > self.best_trade_profit
            ):

                self.best_trade_profit = (
                    profit_usdt
                )

            if (
                self.total_trades == 1
                or
                profit_usdt
                < self.worst_trade_profit
            ):

                self.worst_trade_profit = (
                    profit_usdt
                )

            # =================================================
            # AUSGABE
            # =================================================

            print("")
            print("=" * 70)

            print(
                f"🔥 [PAPER-TRADE] "
                f"{symbol}"
            )

            print(
                f"{buy_ex_name.upper()} "
                f"-> "
                f"{sell_ex_name.upper()}"
            )

            print(
                f"Orderbook BUY: "
                f"{buy_result['average_price']:.8f}"
            )

            print(
                f"Orderbook SELL: "
                f"{sell_result['average_price']:.8f}"
            )

            print(
                f"Netto: "
                f"{real_profit_pct:+.4f}%"
            )

            print(
                f"Gewinn: "
                f"${profit_usdt:+.6f}"
            )

            print(
                f"Paper-Kapital: "
                f"${self.paper_balance:,.4f}"
            )

            print(
                f"Trade #{self.total_trades}"
            )

            print(
                f"Modus: "
                f"{mode_str}"
            )

            print("=" * 70)

            # =================================================
            # CSV
            # =================================================

            try:

                with open(
                    self.csv_file,
                    "a",
                    newline="",
                    encoding="utf-8"
                ) as f:

                    writer = csv.DictWriter(
                        f,
                        fieldnames=[
                            "timestamp",
                            "symbol",
                            "buy_ex",
                            "sell_ex",
                            "buy_price",
                            "sell_price",
                            "raw_margin_pct",
                            "real_profit_pct",
                            "profit_usd",
                            "paper_balance",
                            "execution_mode",
                            "status"
                        ]
                    )

                    writer.writerow({
                        "timestamp":
                            time.strftime(
                                "%Y-%m-%d %H:%M:%S"
                            ),

                        "symbol":
                            symbol,

                        "buy_ex":
                            buy_ex_name.upper(),

                        "sell_ex":
                            sell_ex_name.upper(),

                        "buy_price":
                            round(
                                buy_result[
                                    "average_price"
                                ],
                                10
                            ),

                        "sell_price":
                            round(
                                sell_result[
                                    "average_price"
                                ],
                                10
                            ),

                        "raw_margin_pct":
                            round(
                                real_raw_margin,
                                4
                            ),

                        "real_profit_pct":
                            round(
                                real_profit_pct,
                                4
                            ),

                        "profit_usd":
                            round(
                                profit_usdt,
                                6
                            ),

                        "paper_balance":
                            round(
                                self.paper_balance,
                                6
                            ),

                        "execution_mode":
                            mode_str,

                        "status":
                            "PAPER_EXECUTED"
                    })

            except Exception as e:

                print(
                    f"⚠️ Fehler beim "
                    f"Schreiben der CSV: {e}"
                )

        except Exception as e:

            print(
                f"⚠️ Fehler bei "
                f"{symbol} "
                f"({buy_ex_name}"
                f"->{sell_ex_name}): "
                f"{type(e).__name__}: {e}"
            )

    # =========================================================
    # STATISTIK
    # =========================================================

    def print_statistics(
        self,
        start_time
    ):

        runtime = (
            time.time()
            - start_time
        )

        return_pct = (
            (
                self.paper_balance
                - self.starting_balance
            )
            / self.starting_balance
        ) * 100

        if self.total_trades > 0:

            avg_profit = (
                self.total_profit
                / self.total_trades
            )

            hit_rate = (
                self.profitable_trades
                / self.total_trades
            ) * 100

        else:

            avg_profit = 0.0
            hit_rate = 0.0

        print("")
        print("=" * 70)
        print("🏁 PAPER-TESTLAUF BEENDET")
        print("=" * 70)

        print(
            f"💰 Startkapital: "
            f"${self.starting_balance:,.2f}"
        )

        print(
            f"💰 Endkapital:   "
            f"${self.paper_balance:,.4f}"
        )

        print(
            f"📈 Gesamtgewinn: "
            f"${self.total_profit:+,.4f}"
        )

        print(
            f"📊 Rendite:      "
            f"{return_pct:+.4f}%"
        )

        print(
            f"🔥 Trades:       "
            f"{self.total_trades}"
        )

        print(
            f"✅ Gewinntrades: "
            f"{self.profitable_trades}"
        )

        print(
            f"🎯 Trefferquote: "
            f"{hit_rate:.2f}%"
        )

        print(
            f"💵 Ø Gewinn/Trade: "
            f"${avg_profit:+.6f}"
        )

        print(
            f"🚀 Bester Trade: "
            f"${self.best_trade_profit:+.6f}"
        )

        print(
            f"📉 Schlechtester Trade: "
            f"${self.worst_trade_profit:+.6f}"
        )

        print(
            f"⏱️ Laufzeit: "
            f"{runtime / 60:.2f} Minuten"
        )

        print("=" * 70)

    # =========================================================
    # HAUPTSCHLEIFE
    # =========================================================

    def run_continuous(
        self,
        duration_hours=1,
        delay_seconds=2
    ):

        print("")
        print(
            "🚀 Starte Trader "
            "[PAPERHANDEL (SIMULATION)]..."
        )

        print(
            f"💰 Startkapital: "
            f"${self.starting_balance:.2f}"
        )

        print(
            f"💵 Handelsgröße: "
            f"${self.amount:.2f}"
        )

        print(
            f"🎯 Mindest-Netto: "
            f"{self.min_profit_pct:.2f}%"
        )

        print(
            f"📚 Orderbook-Level: "
            f"{self.orderbook_limit}"
        )

        print(
            f"🛡️ Max. Spread: "
            f"{self.max_raw_margin_pct:.1f}%"
        )

        print(
            f"🔒 Trade-Cooldown: "
            f"{self.trade_cooldown}s"
        )

        print(
            f"⏱️ Laufzeit: "
            f"{duration_hours} Stunde(n) "
            f"| Pause: {delay_seconds}s"
        )

        print("")

        # -----------------------------------------------------
        # MARKETS
        # -----------------------------------------------------

        for name, data in list(
            self.exchanges.items()
        ):

            try:

                data["instance"].load_markets()

                print(
                    f"✅ Märkte geladen für "
                    f"{name.upper()}: "
                    f"{len(data['instance'].markets)} Paare"
                )

            except Exception as e:

                print(
                    f"⚠️ Märkte konnten für "
                    f"{name.upper()} nicht "
                    f"geladen werden: {e}"
                )

        # -----------------------------------------------------
        # START
        # -----------------------------------------------------

        start_time = time.time()

        end_time = (
            start_time
            + duration_hours * 3600
        )

        cycle = 1

        # -----------------------------------------------------
        # LOOP
        # -----------------------------------------------------

        while time.time() < end_time:

            elapsed_min = int(
                (
                    time.time()
                    - start_time
                ) / 60
            )

            print(
                f"\n🔄 Scan-Zyklus "
                f"{cycle} | "
                f"Verstrichene Zeit: "
                f"{elapsed_min} Min. | "
                f"Paper-Kapital: "
                f"${self.paper_balance:.4f}"
            )

            active = list(
                self.exchanges.keys()
            )

            for i in range(
                len(active)
            ):

                for j in range(
                    len(active)
                ):

                    if i == j:
                        continue

                    ex1 = active[i]
                    ex2 = active[j]

                    try:

                        t1 = (
                            self.exchanges[
                                ex1
                            ]["instance"]
                            .fetch_tickers()
                        )

                        t2 = (
                            self.exchanges[
                                ex2
                            ]["instance"]
                            .fetch_tickers()
                        )

                        s1 = {
                            s
                            for s in t1.keys()
                            if s.endswith(
                                "/USDT"
                            )
                        }

                        s2 = {
                            s
                            for s in t2.keys()
                            if s.endswith(
                                "/USDT"
                            )
                        }

                        common = (
                            s1.intersection(s2)
                        )

                        for symbol in common:

                            ticker1 = t1.get(
                                symbol,
                                {}
                            )

                            ticker2 = t2.get(
                                symbol,
                                {}
                            )

                            self.execute_arbitrage(
                                symbol,
                                ex1,
                                ex2,
                                ticker1,
                                ticker2
                            )

                    except Exception as e:

                        print(
                            f"⚠️ Fehler beim "
                            f"Pair-Fetch "
                            f"({ex1}-{ex2}): "
                            f"{type(e).__name__}: "
                            f"{e}"
                        )

            cycle += 1

            time.sleep(
                delay_seconds
            )

        # -----------------------------------------------------
        # ENDERGEBNIS
        # -----------------------------------------------------

        self.print_statistics(
            start_time
        )


# =============================================================
# START
# =============================================================

if __name__ == "__main__":

    trader = MultiExchangeTrader(

        amount_per_trade=10.0,

        starting_balance=1000.0,

        min_profit_pct=0.10,

        dry_run=True
    )

    trader.run_continuous(

        duration_hours=1,

        delay_seconds=2
    )
