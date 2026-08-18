import os
import time
import csv
import ccxt


class MultiExchangeTrader:

    def __init__(
        self,
        starting_capital=1000.0,
        amount_per_trade=1000.0,
        min_profit_pct=0.10,
        dry_run=True
    ):

        # =====================================================
        # SICHERHEIT
        # =====================================================

        self.starting_capital = float(starting_capital)
        self.amount = float(amount_per_trade)
        self.min_profit_pct = float(min_profit_pct)

        # NIEMALS automatisch Echtgeld
        self.dry_run = True if dry_run else False

        # Schutz gegen fehlerhafte Marktdaten
        self.max_raw_margin_pct = 5.0

        # Orderbook
        self.orderbook_limit = 20

        # Gebühren
        self.fees = {
            "okx": 0.001,
            "kucoin": 0.001
        }

        self.exchanges = {}

        # Virtuelle Guthaben
        self.balances = {
            "okx": {
                "usdt": self.starting_capital,
                "coin_value": 0.0
            },
            "kucoin": {
                "usdt": self.starting_capital,
                "coin_value": 0.0
            }
        }

        self.total_profit = 0.0
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0

        self.profits = []

        self.csv_file = "paper_trading_v2_results.csv"
        self.chancen_csv_file = "paper_trading_v2_chancen.csv"

        # =====================================================
        # OKX
        # =====================================================

        try:

            config = {
                "enableRateLimit": True,
                "timeout": 10000,
                "options": {
                    "defaultType": "spot"
                }
            }

            # API-Schlüssel werden im Paperhandel NICHT benötigt
            ex = ccxt.okx(config)

            self.exchanges["okx"] = {
                "instance": ex,
                "fee": self.fees["okx"]
            }

        except Exception as e:

            print(
                f"⚠️ OKX Initialisierungsfehler: {e}"
            )

        # =====================================================
        # KUCOIN
        # =====================================================

        try:

            config = {
                "enableRateLimit": True,
                "timeout": 10000
            }

            ex = ccxt.kucoin(config)

            self.exchanges["kucoin"] = {
                "instance": ex,
                "fee": self.fees["kucoin"]
            }

        except Exception as e:

            print(
                f"⚠️ KuCoin Initialisierungsfehler: {e}"
            )

        self.init_csv()

    # =========================================================
    # CSV
    # =========================================================

    def init_csv(self):

        if not os.path.exists(self.csv_file):

            with open(
                self.csv_file,
                "w",
                newline="",
                encoding="utf-8"
            ) as f:

                writer = csv.writer(f)

                writer.writerow([
                    "timestamp",
                    "symbol",
                    "buy_exchange",
                    "sell_exchange",
                    "capital",
                    "buy_price",
                    "sell_price",
                    "raw_margin_pct",
                    "net_profit_pct",
                    "profit_usdt",
                    "status"
                ])

        if not os.path.exists(self.chancen_csv_file):

            with open(
                self.chancen_csv_file,
                "w",
                newline="",
                encoding="utf-8"
            ) as f:

                writer = csv.writer(f)

                writer.writerow([
                    "timestamp",
                    "symbol",
                    "buy_exchange",
                    "sell_exchange",
                    "raw_margin_pct",
                    "estimated_net_pct",
                    "reason"
                ])

    # =========================================================
    # CHANCE LOG
    # =========================================================

    def log_chance(
        self,
        symbol,
        buy_ex,
        sell_ex,
        raw_margin,
        estimated_net,
        reason
    ):

        with open(
            self.chancen_csv_file,
            "a",
            newline="",
            encoding="utf-8"
        ) as f:

            writer = csv.writer(f)

            writer.writerow([
                time.strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                symbol,
                buy_ex.upper(),
                sell_ex.upper(),
                round(raw_margin, 5),
                round(estimated_net, 5),
                reason
            ])

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
        spent = 0.0

        for level in asks:

            if len(level) < 2:
                continue

            price = float(level[0])
            quantity = float(level[1])

            if price <= 0 or quantity <= 0:
                continue

            available_value = (
                price * quantity
            )

            buy_quantity = min(
                quantity,
                remaining_usdt / price
            )

            cost = (
                buy_quantity * price
            )

            coin_amount += buy_quantity
            spent += cost
            remaining_usdt -= cost

            if remaining_usdt <= 0.00000001:
                break

        if spent < usdt_amount * 0.999:

            return None

        if coin_amount <= 0:

            return None

        return {
            "coin_amount": coin_amount,
            "spent": spent,
            "average_price":
                spent / coin_amount
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
        received = 0.0
        sold = 0.0

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

            received += (
                sell_quantity * price
            )

            sold += sell_quantity
            remaining_coin -= sell_quantity

            if remaining_coin <= 0.00000001:
                break

        if sold < coin_amount * 0.999:

            return None

        if sold <= 0:

            return None

        return {
            "received": received,
            "average_price":
                received / sold
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

            ask = ticker_buy.get("ask")
            bid = ticker_sell.get("bid")

            if not ask or not bid:
                return

            ask = float(ask)
            bid = float(bid)

            if ask <= 0 or bid <= 0:
                return

            # =================================================
            # TICKER SPREAD
            # =================================================

            raw_margin = (
                (bid - ask)
                / ask
            ) * 100

            if raw_margin <= 0:
                return

            # Schutz gegen XTER-Fehler
            if raw_margin > self.max_raw_margin_pct:

                print(
                    f"🛑 [{symbol}] "
                    f"Ungültiger Spread "
                    f"+{raw_margin:.2f}%"
                )

                self.log_chance(
                    symbol,
                    buy_ex_name,
                    sell_ex_name,
                    raw_margin,
                    0,
                    "INVALID_SPREAD"
                )

                return

            # =================================================
            # GEBÜHREN
            # =================================================

            fee_buy = self.fees[
                buy_ex_name
            ]

            fee_sell = self.fees[
                sell_ex_name
            ]

            estimated_net = (
                raw_margin
                - (
                    fee_buy
                    + fee_sell
                ) * 100
            )

            if raw_margin >= 0.05:

                print(
                    f"👀 {symbol} "
                    f"({buy_ex_name.upper()} "
                    f"-> {sell_ex_name.upper()}): "
                    f"Brutto "
                    f"+{raw_margin:.3f}% | "
                    f"Netto geschätzt "
                    f"{estimated_net:+.3f}%"
                )

            if estimated_net < self.min_profit_pct:

                self.log_chance(
                    symbol,
                    buy_ex_name,
                    sell_ex_name,
                    raw_margin,
                    estimated_net,
                    "BELOW_MIN_PROFIT"
                )

                return

            # =================================================
            # KAPITALPRÜFUNG
            # =================================================

            if (
                self.balances[
                    buy_ex_name
                ]["usdt"]
                < self.amount
            ):

                return

            # =================================================
            # ORDERBOOK
            # =================================================

            buy_exchange = self.exchanges[
                buy_ex_name
            ]["instance"]

            sell_exchange = self.exchanges[
                sell_ex_name
            ]["instance"]

            ob_buy = (
                buy_exchange.fetch_order_book(
                    symbol,
                    limit=self.orderbook_limit
                )
            )

            ob_sell = (
                sell_exchange.fetch_order_book(
                    symbol,
                    limit=self.orderbook_limit
                )
            )

            if (
                not ob_buy.get("asks")
                or not ob_sell.get("bids")
            ):

                return

            # =================================================
            # ORDERBOOK SPREAD
            # =================================================

            buy_price = float(
                ob_buy["asks"][0][0]
            )

            sell_price = float(
                ob_sell["bids"][0][0]
            )

            orderbook_margin = (
                (sell_price - buy_price)
                / buy_price
            ) * 100

            if (
                orderbook_margin <= 0
                or orderbook_margin
                > self.max_raw_margin_pct
            ):

                return

            # =================================================
            # REALISTISCHER BUY
            # =================================================

            buy_result = self.simulate_buy(
                ob_buy["asks"],
                self.amount
            )

            if not buy_result:

                self.log_chance(
                    symbol,
                    buy_ex_name,
                    sell_ex_name,
                    orderbook_margin,
                    0,
                    "BUY_LIQUIDITY"
                )

                return

            # Handelsgebühr beim Kauf
            coin_after_buy_fee = (
                buy_result["coin_amount"]
                * (1 - fee_buy)
            )

            # =================================================
            # REALISTISCHER SELL
            # =================================================

            sell_result = self.simulate_sell(
                ob_sell["bids"],
                coin_after_buy_fee
            )

            if not sell_result:

                self.log_chance(
                    symbol,
                    buy_ex_name,
                    sell_ex_name,
                    orderbook_margin,
                    0,
                    "SELL_LIQUIDITY"
                )

                return

            # Verkaufsgebühr
            final_usdt = (
                sell_result["received"]
                * (1 - fee_sell)
            )

            # =================================================
            # GEWINN
            # =================================================

            profit = (
                final_usdt
                - self.amount
            )

            profit_pct = (
                profit
                / self.amount
            ) * 100

            # Schutz
            if profit_pct > self.max_raw_margin_pct:

                return

            # =================================================
            # NICHT PROFITABEL
            # =================================================

            if profit_pct < self.min_profit_pct:

                self.log_chance(
                    symbol,
                    buy_ex_name,
                    sell_ex_name,
                    orderbook_margin,
                    profit_pct,
                    "ORDERBOOK_BELOW_MIN"
                )

                return

            # =================================================
            # VIRTUELLER KAPITALFLUSS
            # =================================================

            # Kaufbörse verliert USDT
            self.balances[
                buy_ex_name
            ]["usdt"] -= self.amount

            # Verkaufsbörse erhält USDT
            self.balances[
                sell_ex_name
            ]["usdt"] += final_usdt

            # Gewinn
            self.total_profit += profit

            self.total_trades += 1
            self.winning_trades += 1

            self.profits.append(profit)

            # =================================================
            # AUSGABE
            # =================================================

            print("")
            print("=" * 70)

            print(
                f"🔥 [PAPER TRADE #{self.total_trades}] "
                f"{symbol}"
            )

            print(
                f"{buy_ex_name.upper()} "
                f"-> "
                f"{sell_ex_name.upper()}"
            )

            print(
                f"💰 Einsatz: "
                f"${self.amount:.2f}"
            )

            print(
                f"📚 BUY Ø: "
                f"{buy_result['average_price']:.8f}"
            )

            print(
                f"📚 SELL Ø: "
                f"{sell_result['average_price']:.8f}"
            )

            print(
                f"📈 Netto: "
                f"+{profit_pct:.4f}%"
            )

            print(
                f"💵 Gewinn: "
                f"+${profit:.6f}"
            )

            print(
                f"🏦 {buy_ex_name.upper()} USDT: "
                f"${self.balances[buy_ex_name]['usdt']:.2f}"
            )

            print(
                f"🏦 {sell_ex_name.upper()} USDT: "
                f"${self.balances[sell_ex_name]['usdt']:.2f}"
            )

            print("=" * 70)

            # =================================================
            # CSV
            # =================================================

            with open(
                self.csv_file,
                "a",
                newline="",
                encoding="utf-8"
            ) as f:

                writer = csv.writer(f)

                writer.writerow([
                    time.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                    symbol,
                    buy_ex_name.upper(),
                    sell_ex_name.upper(),
                    round(self.amount, 4),
                    round(
                        buy_result["average_price"],
                        10
                    ),
                    round(
                        sell_result["average_price"],
                        10
                    ),
                    round(
                        orderbook_margin,
                        5
                    ),
                    round(
                        profit_pct,
                        5
                    ),
                    round(
                        profit,
                        6
                    ),
                    "PAPER_TRADING_V2"
                ])

        except Exception as e:

            print(
                f"⚠️ Fehler bei {symbol} "
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

        print("")
        print(
            "🚀 PAPER TRADER V2 STARTET"
        )

        print(
            f"💰 Startkapital je Börse: "
            f"${self.starting_capital:.2f}"
        )

        print(
            f"💵 Tradegröße: "
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
            "🛡️ Echtgeld: DEAKTIVIERT"
        )

        print(
            f"⏱️ Laufzeit: "
            f"{duration_hours} Stunde(n)"
        )

        print("")

        # =====================================================
        # MARKETS
        # =====================================================

        for name, data in self.exchanges.items():

            try:

                data["instance"].load_markets()

                print(
                    f"✅ Märkte geladen für "
                    f"{name.upper()}: "
                    f"{len(data['instance'].markets)} Paare"
                )

            except Exception as e:

                print(
                    f"⚠️ Marktfehler "
                    f"{name.upper()}: {e}"
                )

        # =====================================================
        # TIMER
        # =====================================================

        start = time.time()

        end = (
            start
            + duration_hours * 3600
        )

        cycle = 1

        # =====================================================
        # LOOP
        # =====================================================

        while time.time() < end:

            elapsed = int(
                (time.time() - start)
                / 60
            )

            print(
                f"\n🔄 Scan-Zyklus {cycle} | "
                f"{elapsed} Min."
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
                            self.exchanges[ex1]
                            ["instance"]
                            .fetch_tickers()
                        )

                        t2 = (
                            self.exchanges[ex2]
                            ["instance"]
                            .fetch_tickers()
                        )

                        common = (
                            set(t1.keys())
                            & set(t2.keys())
                        )

                        common = [
                            s
                            for s in common
                            if s.endswith(
                                "/USDT"
                            )
                        ]

                        for symbol in common:

                            self.execute_arbitrage(
                                symbol,
                                ex1,
                                ex2,
                                t1.get(
                                    symbol,
                                    {}
                                ),
                                t2.get(
                                    symbol,
                                    {}
                                )
                            )

                    except Exception as e:

                        print(
                            f"⚠️ Fetch-Fehler "
                            f"{ex1}->{ex2}: "
                            f"{type(e).__name__}: {e}"
                        )

            cycle += 1

            time.sleep(
                delay_seconds
            )

        # =====================================================
        # ABSCHLUSS
        # =====================================================

        total_capital = (
            self.balances["okx"]["usdt"]
            + self.balances["kucoin"]["usdt"]
        )

        initial_total = (
            self.starting_capital * 2
        )

        total_profit = (
            total_capital
            - initial_total
        )

        return_pct = (
            total_profit
            / initial_total
        ) * 100

        print("")
        print("=" * 70)
        print(
            "🏁 PAPER-TEST V2 BEENDET"
        )
        print("=" * 70)

        print(
            f"💰 Startkapital gesamt: "
            f"${initial_total:,.4f}"
        )

        print(
            f"💰 Endkapital gesamt: "
            f"${total_capital:,.4f}"
        )

        print(
            f"📈 Gesamtgewinn: "
            f"${total_profit:+,.4f}"
        )

        print(
            f"📊 Rendite: "
            f"{return_pct:+.4f}%"
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

        if self.profits:

            avg_profit = (
                sum(self.profits)
                / len(self.profits)
            )

            print(
                f"💵 Ø Gewinn/Trade: "
                f"${avg_profit:+.6f}"
            )

            print(
                f"🚀 Bester Trade: "
                f"${max(self.profits):+.6f}"
            )

            print(
                f"📉 Schlechtester Trade: "
                f"${min(self.profits):+.6f}"
            )

        print(
            f"🏦 OKX USDT: "
            f"${self.balances['okx']['usdt']:.4f}"
        )

        print(
            f"🏦 KuCoin USDT: "
            f"${self.balances['kucoin']['usdt']:.4f}"
        )

        print("=" * 70)


# =============================================================
# START
# =============================================================

if __name__ == "__main__":

    trader = MultiExchangeTrader(
        starting_capital=1000.0,
        amount_per_trade=1000.0,
        min_profit_pct=0.10,
        dry_run=True
    )

    trader.run_continuous(
        duration_hours=1,
        delay_seconds=2
    ) 
