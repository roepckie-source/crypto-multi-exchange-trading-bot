import os
import time
import csv
import ccxt


class MultiExchangeTrader:

    def __init__(
        self,
        amount_per_trade=10.0,
        min_profit_pct=0.10,
        dry_run=True
    ):
        self.amount = amount_per_trade
        self.min_profit_pct = min_profit_pct

        # Sicherheitsgrenze gegen fehlerhafte Marktdaten
        self.max_raw_margin_pct = 5.0

        self.dry_run = dry_run

        self.csv_file = (
            "paper_trading_results.csv"
            if dry_run
            else "live_trading_results.csv"
        )

        self.chancen_csv_file = "log_chancen.csv"

        self.orderbook_limit = 10

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

            okx_key = os.getenv("OKX_API_KEY", "")

            if okx_key and not dry_run:
                okx_config.update({
                    "apiKey": okx_key,
                    "secret": os.getenv("OKX_API_SECRET", ""),
                    "password": os.getenv("OKX_PASSPRASE", "")
                })

            ex = ccxt.okx(okx_config)

            self.exchanges["okx"] = {
                "instance": ex,
                "fee": 0.001
            }

        except Exception as e:
            print(f"⚠️ OKX Initialisierungsfehler: {e}")

        # =====================================================
        # KUCOIN
        # =====================================================

        try:
            kucoin_config = {
                "enableRateLimit": True,
                "timeout": 10000
            }

            kucoin_key = os.getenv("KUCOIN_API_KEY", "")

            if kucoin_key and not dry_run:
                kucoin_config.update({
                    "apiKey": kucoin_key,
                    "secret": os.getenv("KUCOIN_API_SECRET", ""),
                    "password": os.getenv("KUCOIN_PASSPRASE", "")
                })

            ex = ccxt.kucoin(kucoin_config)

            self.exchanges["kucoin"] = {
                "instance": ex,
                "fee": 0.001
            }

        except Exception as e:
            print(f"⚠️ KuCoin Initialisierungsfehler: {e}")

        self.init_csv()

    # =========================================================
    # CSV
    # =========================================================

    def init_csv(self):

        if not os.path.exists(self.csv_file):

            with open(
                self.csv_file,
                mode="w",
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
                        "execution_mode",
                        "status"
                    ]
                )

                writer.writeheader()

        if not os.path.exists(self.chancen_csv_file):

            with open(
                self.chancen_csv_file,
                mode="w",
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

        with open(
            self.chancen_csv_file,
            mode="a",
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
                "timestamp": time.strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "symbol": symbol,
                "buy_ex": buy_ex.upper(),
                "sell_ex": sell_ex.upper(),
                "ask_buy": ask_buy,
                "bid_sell": bid_sell,
                "raw_margin_pct": round(raw_margin, 4),
                "estimated_net_pct": round(
                    estimated_net,
                    4
                ),
                "reason": reason
            })

    # =========================================================
    # BUY ORDERBOOK SIMULATION
    # =========================================================

    def simulate_buy(
        self,
        asks,
        usdt_amount
    ):
        """
        Berechnet, wie viel Coin tatsächlich für
        den angegebenen USDT-Betrag gekauft werden kann.
        """

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

            level_value = price * quantity

            if level_value <= remaining_usdt:
                buy_quantity = quantity
            else:
                buy_quantity = remaining_usdt / price

            cost = buy_quantity * price

            coin_amount += buy_quantity
            spent_usdt += cost
            remaining_usdt -= cost

            if remaining_usdt <= 0.00000001:
                break

        # Nicht genügend Liquidität
        if spent_usdt < usdt_amount * 0.999:

            return None

        average_price = (
            spent_usdt / coin_amount
        )

        return {
            "coin_amount": coin_amount,
            "spent_usdt": spent_usdt,
            "average_price": average_price
        }

    # =========================================================
    # SELL ORDERBOOK SIMULATION
    # =========================================================

    def simulate_sell(
        self,
        bids,
        coin_amount
    ):
        """
        Berechnet den tatsächlichen Erlös beim Verkauf
        über mehrere Bid-Level.
        """

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
                sell_quantity * price
            )

            sold_coin += sell_quantity
            remaining_coin -= sell_quantity

            if remaining_coin <= 0.00000001:
                break

        # Nicht genügend Liquidität
        if sold_coin < coin_amount * 0.999:

            return None

        average_price = (
            received_usdt / sold_coin
        )

        return {
            "received_usdt": received_usdt,
            "average_price": average_price
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

            ask_buy = ticker_buy.get("ask")
            bid_sell = ticker_sell.get("bid")

            if not ask_buy or not bid_sell:
                return

            ask_buy = float(ask_buy)
            bid_sell = float(bid_sell)

            if ask_buy <= 0 or bid_sell <= 0:
                return

            # -------------------------------------------------
            # Plausibilitätsprüfung
            # -------------------------------------------------

            raw_margin = (
                (bid_sell - ask_buy)
                / ask_buy
            ) * 100

            # Negative Arbitrage
            if raw_margin <= 0:
                return

            # Schutz gegen XTER-artige Fehler
            if raw_margin > self.max_raw_margin_pct:

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
            # Gebühren
            # -------------------------------------------------

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
                raw_margin - total_fee_pct
            )

            # Nur interessante Ticker anzeigen
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

            # -------------------------------------------------
            # Noch keine Orderbook-Prüfung nötig
            # -------------------------------------------------

            if estimated_net < self.min_profit_pct:

                self.log_chance(
                    symbol,
                    buy_ex_name,
                    sell_ex_name,
                    ask_buy,
                    bid_sell,
                    raw_margin,
                    estimated_net,
                    "BELOW_MIN_PROFIT"
                )

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
                return

            real_buy_price = float(
                ob_buy["asks"][0][0]
            )

            real_sell_price = float(
                ob_sell["bids"][0][0]
            )

            # -------------------------------------------------
            # Erneute Plausibilitätsprüfung
            # -------------------------------------------------

            real_raw_margin = (
                (real_sell_price - real_buy_price)
                / real_buy_price
            ) * 100

            if (
                real_raw_margin <= 0
                or real_raw_margin > self.max_raw_margin_pct
            ):

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

            # -------------------------------------------------
            # REALER BUY
            # -------------------------------------------------

            buy_result = self.simulate_buy(
                ob_buy["asks"],
                self.amount
            )

            if not buy_result:

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

            coin_amount = (
                buy_result["coin_amount"]
                * (1 - fee_buy)
            )

            # -------------------------------------------------
            # REALER SELL
            # -------------------------------------------------

            sell_result = self.simulate_sell(
                ob_sell["bids"],
                coin_amount
            )

            if not sell_result:

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

            final_usdt = (
                sell_result["received_usdt"]
                * (1 - fee_sell)
            )

            # -------------------------------------------------
            # ECHTER NETTO-GEWINN
            # -------------------------------------------------

            profit_usdt = (
                final_usdt - self.amount
            )

            real_profit_pct = (
                profit_usdt / self.amount
            ) * 100

            # -------------------------------------------------
            # MAX-PROFIT-SCHUTZ
            # -------------------------------------------------

            if real_profit_pct > self.max_raw_margin_pct:

                print(
                    f"🛑 [{symbol}] "
                    f"Unplausibler Netto-Gewinn "
                    f"+{real_profit_pct:.3f}% "
                    f"→ VERWORFEN"
                )

                return

            # -------------------------------------------------
            # NOCH NICHT PROFITABEL
            # -------------------------------------------------

            if real_profit_pct < self.min_profit_pct:

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

                return

            # =================================================
            # ECHTE PAPER-CHANCE
            # =================================================

            mode_str = (
                "PAPER_TRADING"
                if self.dry_run
                else "LIVE_REAL_MONEY"
            )

            print("")
            print("=" * 70)

            print(
                f"🔥 [TRADE-KANDIDAT] {symbol}"
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
                f"+{real_profit_pct:.4f}%"
            )

            print(
                f"Gewinn: "
                f"+${profit_usdt:.6f}"
            )

            print(
                f"Modus: {mode_str}"
            )

            print("=" * 70)

            # -------------------------------------------------
            # CSV
            # -------------------------------------------------

            with open(
                self.csv_file,
                mode="a",
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
                        "execution_mode",
                        "status"
                    ]
                )

                writer.writerow({
                    "timestamp": time.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                    "symbol": symbol,
                    "buy_ex": buy_ex_name.upper(),
                    "sell_ex": sell_ex_name.upper(),
                    "buy_price": round(
                        buy_result["average_price"],
                        10
                    ),
                    "sell_price": round(
                        sell_result["average_price"],
                        10
                    ),
                    "raw_margin_pct": round(
                        real_raw_margin,
                        4
                    ),
                    "real_profit_pct": round(
                        real_profit_pct,
                        4
                    ),
                    "profit_usd": round(
                        profit_usdt,
                        6
                    ),
                    "execution_mode": mode_str,
                    "status": "PAPER_READY"
                })

        except Exception as e:

            print(
                f"⚠️ Fehler bei "
                f"{symbol} "
                f"({buy_ex_name}->{sell_ex_name}): "
                f"{type(e).__name__}: {e}"
            )

    # =========================================================
    # RUN
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
            f"🚀 Starte Trader [{mode_label}]..."
        )

        print(
            f"💰 Tradegröße: "
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
            f"🛡️ Max. zulässige Bruttomarge: "
            f"{self.max_raw_margin_pct:.1f}%"
        )

        print(
            f"⏱️ Laufzeit: "
            f"{duration_hours} Stunde(n) | "
            f"Pause: {delay_seconds}s"
        )

        print("")

        # -----------------------------------------------------
        # Märkte laden
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
                    f"{name.upper()} nicht geladen werden: "
                    f"{e}"
                )

        # -----------------------------------------------------
        # Hauptschleife
        # -----------------------------------------------------

        start_time = time.time()

        end_time = (
            start_time
            + duration_hours * 3600
        )

        cycle = 1

        while time.time() < end_time:

            elapsed_min = int(
                (time.time() - start_time)
                / 60
            )

            print(
                f"\n🔄 Scan-Zyklus {cycle} | "
                f"Verstrichene Zeit: "
                f"{elapsed_min} Min."
            )

            active = list(
                self.exchanges.keys()
            )

            for i in range(len(active)):

                for j in range(len(active)):

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
                            if s.endswith("/USDT")
                        }

                        s2 = {
                            s
                            for s in t2.keys()
                            if s.endswith("/USDT")
                        }

                        common = s1.intersection(s2)

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

        print("")
        print(
            "🏁 Paper-Testlauf beendet."
        )


# =============================================================
# START
# =============================================================

if __name__ == "__main__":

    trader = MultiExchangeTrader(
        amount_per_trade=10.0,
        min_profit_pct=0.10,
        dry_run=True
    )

    trader.run_continuous(
        duration_hours=1,
        delay_seconds=2
    )
