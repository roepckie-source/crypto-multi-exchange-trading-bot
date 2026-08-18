import os
import time
import csv
import ccxt


class MultiExchangeTrader:

    def __init__(
        self,
        amount_per_trade=1000.0,
        starting_balance_per_exchange=1000.0,
        min_profit_pct=0.10,
        dry_run=True
    ):

        # =====================================================
        # GRUNDEINSTELLUNGEN
        # =====================================================

        self.amount = float(amount_per_trade)

        self.starting_balance_per_exchange = float(
            starting_balance_per_exchange
        )

        self.min_profit_pct = float(min_profit_pct)

        # Sicherheitsgrenze gegen fehlerhafte Marktdaten
        self.max_raw_margin_pct = 5.0

        self.dry_run = dry_run

        # KuCoin akzeptiert bei Orderbook u.a. 20 oder 100
        self.orderbook_limit = 20

        # Gebühren
        self.default_fee = 0.001  # 0,10 %

        # =====================================================
        # KAPITAL
        # =====================================================

        self.balances = {
            "okx": self.starting_balance_per_exchange,
            "kucoin": self.starting_balance_per_exchange
        }

        self.starting_total_balance = (
            self.starting_balance_per_exchange * 2
        )

        # =====================================================
        # STATISTIK
        # =====================================================

        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0

        self.total_profit = 0.0

        self.trade_profits = []

        self.rejected_orderbook = 0
        self.rejected_liquidity = 0
        self.rejected_profit = 0
        self.invalid_spreads = 0

        # =====================================================
        # CSV
        # =====================================================

        self.csv_file = (
            "paper_trading_results_v3.csv"
            if dry_run
            else "live_trading_results_v3.csv"
        )

        self.chancen_csv_file = "log_chancen_v3.csv"

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
                "fee": self.default_fee
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

            ex = ccxt.kucoin(
                kucoin_config
            )

            self.exchanges["kucoin"] = {
                "instance": ex,
                "fee": self.default_fee
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

        if not os.path.exists(
            self.csv_file
        ):

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
                        "trade_amount",
                        "buy_price",
                        "sell_price",
                        "raw_margin_pct",
                        "real_profit_pct",
                        "profit_usdt",
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
    # CHANCE LOGGEN
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
                            5
                        ),

                    "estimated_net_pct":
                        round(
                            estimated_net,
                            5
                        ),

                    "reason":
                        reason
                })

        except Exception:
            pass

    # =========================================================
    # BUY ORDERBOOK
    # =========================================================

    def simulate_buy(
        self,
        asks,
        usdt_amount
    ):

        remaining_usdt = float(
            usdt_amount
        )

        coin_amount = 0.0
        spent_usdt = 0.0

        levels_used = 0

        for level in asks:

            if len(level) < 2:
                continue

            try:

                price = float(
                    level[0]
                )

                quantity = float(
                    level[1]
                )

            except Exception:
                continue

            if price <= 0 or quantity <= 0:
                continue

            available_value = (
                price * quantity
            )

            if available_value <= remaining_usdt:

                buy_quantity = quantity

            else:

                buy_quantity = (
                    remaining_usdt / price
                )

            cost = (
                buy_quantity * price
            )

            coin_amount += buy_quantity

            spent_usdt += cost

            remaining_usdt -= cost

            levels_used += 1

            if remaining_usdt <= 0.00000001:
                break

        if spent_usdt < (
            usdt_amount * 0.999
        ):

            return None

        if coin_amount <= 0:
            return None

        average_price = (
            spent_usdt / coin_amount
        )

        return {

            "coin_amount":
                coin_amount,

            "spent_usdt":
                spent_usdt,

            "average_price":
                average_price,

            "levels_used":
                levels_used
        }

    # =========================================================
    # SELL ORDERBOOK
    # =========================================================

    def simulate_sell(
        self,
        bids,
        coin_amount
    ):

        remaining_coin = float(
            coin_amount
        )

        received_usdt = 0.0

        sold_coin = 0.0

        levels_used = 0

        for level in bids:

            if len(level) < 2:
                continue

            try:

                price = float(
                    level[0]
                )

                quantity = float(
                    level[1]
                )

            except Exception:
                continue

            if price <= 0 or quantity <= 0:
                continue

            sell_quantity = min(
                remaining_coin,
                quantity
            )

            received_usdt += (
                sell_quantity * price
            )

            sold_coin += sell_quantity

            remaining_coin -= (
                sell_quantity
            )

            levels_used += 1

            if remaining_coin <= 0.00000001:
                break

        if sold_coin < (
            coin_amount * 0.999
        ):

            return None

        if sold_coin <= 0:
            return None

        average_price = (
            received_usdt / sold_coin
        )

        return {

            "received_usdt":
                received_usdt,

            "average_price":
                average_price,

            "sold_coin":
                sold_coin,

            "levels_used":
                levels_used
        }

    # =========================================================
    # ARBITRAGE PRÜFEN
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

            if ask_buy <= 0 or bid_sell <= 0:
                return

            # =================================================
            # TICKER SPREAD
            # =================================================

            raw_margin = (
                (
                    bid_sell - ask_buy
                )
                / ask_buy
            ) * 100

            if raw_margin <= 0:
                return

            # =================================================
            # XTER / FEHLERDATEN SCHUTZ
            # =================================================

            if raw_margin > (
                self.max_raw_margin_pct
            ):

                print(
                    f"🛑 [{symbol}] "
                    f"Ungültiger Spread "
                    f"+{raw_margin:.3f}% "
                    f"→ VERWORFEN"
                )

                self.invalid_spreads += 1

                self.log_chance(
                    symbol,
                    buy_ex_name,
                    sell_ex_name,
                    ask_buy,
                    bid_sell,
                    raw_margin,
                    0,
                    "INVALID_TICKER_SPREAD"
                )

                return

            # =================================================
            # GEBÜHREN
            # =================================================

            fee_buy = self.exchanges[
                buy_ex_name
            ]["fee"]

            fee_sell = self.exchanges[
                sell_ex_name
            ]["fee"]

            total_fee_pct = (
                fee_buy + fee_sell
            ) * 100

            estimated_net = (
                raw_margin
                - total_fee_pct
            )

            # =================================================
            # TICKER AUSGABE
            # =================================================

            if raw_margin >= 0.05:

                print(
                    f"👀 {symbol} "
                    f"({buy_ex_name.upper()} "
                    f"-> {sell_ex_name.upper()}): "
                    f"Ticker-Brutto "
                    f"+{raw_margin:.3f}% | "
                    f"geschätzt Netto "
                    f"{estimated_net:+.3f}%"
                )

            # =================================================
            # TICKER NICHT PROFITABEL
            # =================================================

            if estimated_net < (
                self.min_profit_pct
            ):

                self.rejected_profit += 1

                self.log_chance(
                    symbol,
                    buy_ex_name,
                    sell_ex_name,
                    ask_buy,
                    bid_sell,
                    raw_margin,
                    estimated_net,
                    "TICKER_BELOW_MIN_PROFIT"
                )

                return

            # =================================================
            # KAPITALPRÜFUNG
            # =================================================

            available_balance = self.balances.get(
                buy_ex_name,
                0.0
            )

            if available_balance < self.amount:

                print(
                    f"💰 [{symbol}] "
                    f"VERWORFEN: "
                    f"Kapital auf "
                    f"{buy_ex_name.upper()} "
                    f"nur "
                    f"${available_balance:.2f}"
                )

                self.log_chance(
                    symbol,
                    buy_ex_name,
                    sell_ex_name,
                    ask_buy,
                    bid_sell,
                    raw_margin,
                    estimated_net,
                    "INSUFFICIENT_CAPITAL"
                )

                return

            # =================================================
            # ORDERBOOK LADEN
            # =================================================

            buy_ex = self.exchanges[
                buy_ex_name
            ]["instance"]

            sell_ex = self.exchanges[
                sell_ex_name
            ]["instance"]

            print(
                f"🔎 ORDERBOOK-CHECK "
                f"{symbol} "
                f"({buy_ex_name.upper()} "
                f"-> {sell_ex_name.upper()})"
            )

            ob_buy = buy_ex.fetch_order_book(
                symbol,
                limit=self.orderbook_limit
            )

            ob_sell = sell_ex.fetch_order_book(
                symbol,
                limit=self.orderbook_limit
            )

            if (
                not ob_buy.get("asks")
                or not ob_sell.get("bids")
            ):

                self.rejected_orderbook += 1

                print(
                    f"❌ [{symbol}] "
                    f"VERWORFEN: "
                    f"Orderbook leer"
                )

                return

            # =================================================
            # BESTE ORDERBOOK PREISE
            # =================================================

            real_buy_price = float(
                ob_buy["asks"][0][0]
            )

            real_sell_price = float(
                ob_sell["bids"][0][0]
            )

            if (
                real_buy_price <= 0
                or real_sell_price <= 0
            ):
                return

            # =================================================
            # ORDERBOOK SPREAD
            # =================================================

            real_raw_margin = (
                (
                    real_sell_price
                    - real_buy_price
                )
                / real_buy_price
            ) * 100

            if (
                real_raw_margin <= 0
                or real_raw_margin
                > self.max_raw_margin_pct
            ):

                self.rejected_orderbook += 1

                print(
                    f"❌ [{symbol}] "
                    f"VERWORFEN: "
                    f"Orderbook-Spread "
                    f"{real_raw_margin:+.3f}%"
                )

                self.log_chance(
                    symbol,
                    buy_ex_name,
                    sell_ex_name,
                    real_buy_price,
                    real_sell_price,
                    real_raw_margin,
                    0,
                    "INVALID_ORDERBOOK_SPREAD"
                )

                return

            # =================================================
            # REALER BUY ÜBER 20 LEVEL
            # =================================================

            buy_result = self.simulate_buy(
                ob_buy["asks"],
                self.amount
            )

            if not buy_result:

                self.rejected_liquidity += 1

                print(
                    f"❌ [{symbol}] "
                    f"VERWORFEN: "
                    f"Nicht genügend BUY-Liquidität "
                    f"für ${self.amount:.2f}"
                )

                self.log_chance(
                    symbol,
                    buy_ex_name,
                    sell_ex_name,
                    real_buy_price,
                    real_sell_price,
                    real_raw_margin,
                    0,
                    "LOW_BUY_LIQUIDITY"
                )

                return

            # =================================================
            # COIN NACH BUY-GEBÜHR
            # =================================================

            coin_amount = (
                buy_result["coin_amount"]
                * (1 - fee_buy)
            )

            # =================================================
            # REALER SELL ÜBER 20 LEVEL
            # =================================================

            sell_result = self.simulate_sell(
                ob_sell["bids"],
                coin_amount
            )

            if not sell_result:

                self.rejected_liquidity += 1

                print(
                    f"❌ [{symbol}] "
                    f"VERWORFEN: "
                    f"Nicht genügend SELL-Liquidität"
                )

                self.log_chance(
                    symbol,
                    buy_ex_name,
                    sell_ex_name,
                    real_buy_price,
                    real_sell_price,
                    real_raw_margin,
                    0,
                    "LOW_SELL_LIQUIDITY"
                )

                return

            # =================================================
            # SELL-GEBÜHR
            # =================================================

            final_usdt = (
                sell_result["received_usdt"]
                * (1 - fee_sell)
            )

            # =================================================
            # ECHTER NETTO-GEWINN
            # =================================================

            profit_usdt = (
                final_usdt
                - self.amount
            )

            real_profit_pct = (
                profit_usdt
                / self.amount
            ) * 100

            # =================================================
            # DETAILAUSGABE
            # =================================================

            print(
                f"   Ticker-Brutto: "
                f"{raw_margin:+.4f}%"
            )

            print(
                f"   Orderbook-Brutto: "
                f"{real_raw_margin:+.4f}%"
            )

            print(
                f"   Gebühren: "
                f"-{total_fee_pct:.4f}%"
            )

            print(
                f"   Orderbook BUY Ø: "
                f"{buy_result['average_price']:.10f}"
            )

            print(
                f"   Orderbook SELL Ø: "
                f"{sell_result['average_price']:.10f}"
            )

            print(
                f"   BUY-Level benutzt: "
                f"{buy_result['levels_used']}"
            )

            print(
                f"   SELL-Level benutzt: "
                f"{sell_result['levels_used']}"
            )

            print(
                f"   Tatsächliches Netto: "
                f"{real_profit_pct:+.4f}%"
            )

            print(
                f"   Ergebnis: "
                f"${profit_usdt:+.6f}"
            )

            # =================================================
            # UNTER MINDESTGEWINN
            # =================================================

            if real_profit_pct < (
                self.min_profit_pct
            ):

                self.rejected_profit += 1

                print(
                    f"❌ [{symbol}] "
                    f"VERWORFEN: "
                    f"Orderbook-Netto "
                    f"{real_profit_pct:+.4f}% "
                    f"< "
                    f"{self.min_profit_pct:.2f}%"
                )

                self.log_chance(
                    symbol,
                    buy_ex_name,
                    sell_ex_name,
                    real_buy_price,
                    real_sell_price,
                    real_raw_margin,
                    real_profit_pct,
                    "ORDERBOOK_BELOW_MIN_PROFIT"
                )

                print(
                    "-" * 70
                )

                return

            # =================================================
            # MAX PROFIT SCHUTZ
            # =================================================

            if real_profit_pct > (
                self.max_raw_margin_pct
            ):

                self.invalid_spreads += 1

                print(
                    f"🛑 [{symbol}] "
                    f"Unplausibler Netto-Gewinn "
                    f"+{real_profit_pct:.3f}% "
                    f"→ VERWORFEN"
                )

                return

            # =================================================
            # PAPER TRADE
            # =================================================

            mode_str = (
                "PAPER_TRADING"
                if self.dry_run
                else "LIVE_REAL_MONEY"
            )

            self.total_trades += 1

            self.winning_trades += 1

            self.total_profit += (
                profit_usdt
            )

            self.trade_profits.append(
                profit_usdt
            )

            # Kapital beim BUY reduzieren
            self.balances[
                buy_ex_name
            ] -= self.amount

            # Verkaufserlös auf SELL-Börse gutschreiben
            self.balances[
                sell_ex_name
            ] += final_usdt

            print("")
            print("=" * 70)

            print(
                f"🔥 [PAPER TRADE] "
                f"{symbol}"
            )

            print(
                f"{buy_ex_name.upper()} "
                f"-> "
                f"{sell_ex_name.upper()}"
            )

            print(
                f"Einsatz: "
                f"${self.amount:,.2f}"
            )

            print(
                f"BUY Ø: "
                f"{buy_result['average_price']:.10f}"
            )

            print(
                f"SELL Ø: "
                f"{sell_result['average_price']:.10f}"
            )

            print(
                f"Netto: "
                f"+{real_profit_pct:.4f}%"
            )

            print(
                f"Gewinn: "
                f"+${profit_usdt:.6f}"
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
                            "trade_amount",
                            "buy_price",
                            "sell_price",
                            "raw_margin_pct",
                            "real_profit_pct",
                            "profit_usdt",
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

                        "trade_amount":
                            round(
                                self.amount,
                                4
                            ),

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
                                5
                            ),

                        "real_profit_pct":
                            round(
                                real_profit_pct,
                                5
                            ),

                        "profit_usdt":
                            round(
                                profit_usdt,
                                6
                            ),

                        "execution_mode":
                            mode_str,

                        "status":
                            "PAPER_EXECUTED"
                    })

            except Exception as e:

                print(
                    f"⚠️ CSV-Fehler: {e}"
                )

        except Exception as e:

            print(
                f"⚠️ Fehler bei "
                f"{symbol} "
                f"({buy_ex_name}->{sell_ex_name}): "
                f"{type(e).__name__}: {e}"
            )

    # =========================================================
    # STATISTIK
    # =========================================================

    def print_statistics(
        self,
        runtime_seconds
    ):

        end_total = sum(
            self.balances.values()
        )

        total_return_pct = (
            (
                end_total
                - self.starting_total_balance
            )
            / self.starting_total_balance
        ) * 100

        if self.trade_profits:

            average_profit = (
                sum(
                    self.trade_profits
                )
                / len(
                    self.trade_profits
                )
            )

            best_trade = max(
                self.trade_profits
            )

            worst_trade = min(
                self.trade_profits
            )

        else:

            average_profit = 0.0
            best_trade = 0.0
            worst_trade = 0.0

        if self.total_trades > 0:

            win_rate = (
                self.winning_trades
                / self.total_trades
            ) * 100

        else:

            win_rate = 0.0

        print("")
        print("=" * 70)

        print(
            "🏁 V3 PAPER-TEST BEENDET"
        )

        print("=" * 70)

        print(
            f"💰 Startkapital gesamt: "
            f"${self.starting_total_balance:,.2f}"
        )

        print(
            f"💰 Endkapital gesamt:   "
            f"${end_total:,.4f}"
        )

        print(
            f"📈 Gesamtgewinn: "
            f"${self.total_profit:+.6f}"
        )

        print(
            f"📊 Rendite: "
            f"{total_return_pct:+.4f}%"
        )

        print(
            f"🔥 Trades: "
            f"{self.total_trades}"
        )

        print(
            f"✅ Gewinntrades: "
            f"{self.winning_trades}"
        )

        print(
            f"❌ Verlusttrades: "
            f"{self.losing_trades}"
        )

        print(
            f"🎯 Trefferquote: "
            f"{win_rate:.2f}%"
        )

        print(
            f"💵 Ø Gewinn/Trade: "
            f"${average_profit:+.6f}"
        )

        print(
            f"🚀 Bester Trade: "
            f"${best_trade:+.6f}"
        )

        print(
            f"📉 Schlechtester Trade: "
            f"${worst_trade:+.6f}"
        )

        print("")

        print(
            f"🏦 OKX USDT: "
            f"${self.balances['okx']:,.4f}"
        )

        print(
            f"🏦 KuCoin USDT: "
            f"${self.balances['kucoin']:,.4f}"
        )

        print("")

        print(
            f"🛑 Ungültige Spreads: "
            f"{self.invalid_spreads}"
        )

        print(
            f"💧 Liquidität verworfen: "
            f"{self.rejected_liquidity}"
        )

        print(
            f"📚 Orderbook verworfen: "
            f"{self.rejected_orderbook}"
        )

        print(
            f"📉 Gewinnschwelle verworfen: "
            f"{self.rejected_profit}"
        )

        print("")

        print(
            f"⏱️ Laufzeit: "
            f"{runtime_seconds / 60:.2f} Minuten"
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

        mode_label = (
            "PAPERHANDEL (SIMULATION)"
            if self.dry_run
            else "LIVE TRADING (ECHTGELD)"
        )

        print("")
        print(
            f"🚀 Starte Trader "
            f"[{mode_label}]..."
        )

        print(
            f"💰 Handelsgröße: "
            f"${self.amount:,.2f}"
        )

        print(
            f"🏦 Startkapital pro Börse: "
            f"${self.starting_balance_per_exchange:,.2f}"
        )

        print(
            f"💰 Gesamtes Startkapital: "
            f"${self.starting_total_balance:,.2f}"
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
            f"🛡️ Max. Bruttomarge: "
            f"{self.max_raw_margin_pct:.1f}%"
        )

        print(
            f"⏱️ Laufzeit: "
            f"{duration_hours} Stunde(n) | "
            f"Pause: {delay_seconds}s"
        )

        print("")

        # =====================================================
        # MÄRKTE LADEN
        # =====================================================

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
                    f"{name.upper()} nicht geladen werden: "
                    f"{e}"
                )

        # =====================================================
        # TIMER
        # =====================================================

        start_time = time.time()

        end_time = (
            start_time
            + duration_hours * 3600
        )

        cycle = 1

        # =====================================================
        # SCAN
        # =====================================================

        while time.time() < end_time:

            elapsed_min = int(
                (
                    time.time()
                    - start_time
                )
                / 60
            )

            print("")
            print(
                f"🔄 Scan-Zyklus "
                f"{cycle} | "
                f"Verstrichene Zeit: "
                f"{elapsed_min} Min."
            )

            active = list(
                self.exchanges.keys()
            )

            # =================================================
            # BÖRSEN VERGLEICHEN
            # =================================================

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
                            self.exchanges[ex1]
                            ["instance"]
                            .fetch_tickers()
                        )

                        t2 = (
                            self.exchanges[ex2]
                            ["instance"]
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
                            s1.intersection(
                                s2
                            )
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
                            f"{type(e).__name__}: {e}"
                        )

            cycle += 1

            time.sleep(
                delay_seconds
            )

        # =====================================================
        # STATISTIK
        # =====================================================

        runtime_seconds = (
            time.time()
            - start_time
        )

        self.print_statistics(
            runtime_seconds
        )


# =============================================================
# START
# =============================================================

if __name__ == "__main__":

    trader = MultiExchangeTrader(

        # =============================================
        # 1.000 USDT PRO TRADE
        # =============================================

        amount_per_trade=1000.0,

        # =============================================
        # 1.000 USDT AUF JEDER BÖRSE
        # =============================================

        starting_balance_per_exchange=1000.0,

        # =============================================
        # MINDESTGEWINN 0,10 %
        # =============================================

        min_profit_pct=0.10,

        # =============================================
        # GANZ WICHTIG:
        # KEINE ECHTEN ORDERS
        # =============================================

        dry_run=True
    )

    trader.run_continuous(

        # 1 Stunde testen
        duration_hours=1,

        # alle 2 Sekunden neuer Scan
        delay_seconds=2
    )
