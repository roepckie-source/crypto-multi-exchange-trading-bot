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
        self.starting_balance_per_exchange = float(starting_balance_per_exchange)
        self.min_profit_pct = float(min_profit_pct)
        self.max_raw_margin_pct = 5.0          # Schutz gegen fehlerhafte Daten
        self.dry_run = dry_run
        self.orderbook_limit = 20
        self.default_fee = 0.001               # 0,10 %

        # =====================================================
        # KAPITAL
        # =====================================================
        self.balances = {
            "okx": self.starting_balance_per_exchange,
            "kucoin": self.starting_balance_per_exchange,
            "bitrue": self.starting_balance_per_exchange,
        }
        self.starting_total_balance = (
            self.starting_balance_per_exchange * len(self.balances)
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
                "options": {"defaultType": "spot"}
            }
            okx_key = os.getenv("OKX_API_KEY", "")
            if okx_key and not dry_run:
                okx_config.update({
                    "apiKey": okx_key,
                    "secret": os.getenv("OKX_API_SECRET", ""),
                    "password": os.getenv("OKX_PASSPHRASE", "")
                })
            ex = ccxt.okx(okx_config)
            self.exchanges["okx"] = {"instance": ex, "fee": self.default_fee}
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
                    "password": os.getenv("KUCOIN_PASSPHRASE", "")
                })
            ex = ccxt.kucoin(kucoin_config)
            self.exchanges["kucoin"] = {"instance": ex, "fee": self.default_fee}
        except Exception as e:
            print(f"⚠️ KuCoin Initialisierungsfehler: {e}")

        # =====================================================
        # BITRUE (neu)
        # =====================================================
        try:
            bitrue_config = {
                "enableRateLimit": True,
                "timeout": 10000,
                "options": {"defaultType": "spot"}
            }
            bitrue_key = os.getenv("BITRUE_API_KEY", "")
            if bitrue_key and not dry_run:
                bitrue_config.update({
                    "apiKey": bitrue_key,
                    "secret": os.getenv("BITRUE_API_SECRET", "")
                })
            ex = ccxt.bitrue(bitrue_config)
            self.exchanges["bitrue"] = {"instance": ex, "fee": self.default_fee}
        except Exception as e:
            print(f"⚠️ Bitrue Initialisierungsfehler: {e}")

        self.init_csv()

    # =========================================================
    # CSV INITIALISIEREN
    # =========================================================
    def init_csv(self):
        if not os.path.exists(self.csv_file):
            with open(self.csv_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "timestamp", "symbol", "buy_ex", "sell_ex",
                        "trade_amount", "buy_price", "sell_price",
                        "raw_margin_pct", "real_profit_pct", "profit_usdt",
                        "execution_mode", "status"
                    ]
                )
                writer.writeheader()

        if not os.path.exists(self.chancen_csv_file):
            with open(self.chancen_csv_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "timestamp", "symbol", "buy_ex", "sell_ex",
                        "ask_buy", "bid_sell", "raw_margin_pct",
                        "estimated_net_pct", "reason"
                    ]
                )
                writer.writeheader()

    # =========================================================
    # CHANCE LOGGEN
    # =========================================================
    def log_chance(self, symbol, buy_ex, sell_ex, ask_buy, bid_sell,
                   raw_margin, estimated_net, reason):
        try:
            with open(self.chancen_csv_file, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "timestamp", "symbol", "buy_ex", "sell_ex",
                        "ask_buy", "bid_sell", "raw_margin_pct",
                        "estimated_net_pct", "reason"
                    ]
                )
                writer.writerow({
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "symbol": symbol,
                    "buy_ex": buy_ex.upper(),
                    "sell_ex": sell_ex.upper(),
                    "ask_buy": ask_buy,
                    "bid_sell": bid_sell,
                    "raw_margin_pct": round(raw_margin, 5),
                    "estimated_net_pct": round(estimated_net, 5),
                    "reason": reason
                })
        except Exception:
            pass

    # =========================================================
    # BUY ORDERBOOK SIMULATION
    # =========================================================
    def simulate_buy(self, asks, usdt_amount):
        remaining_usdt = float(usdt_amount)
        coin_amount = 0.0
        spent_usdt = 0.0
        levels_used = 0

        for level in asks:
            if len(level) < 2:
                continue
            try:
                price = float(level[0])
                quantity = float(level[1])
            except Exception:
                continue
            if price <= 0 or quantity <= 0:
                continue

            available_value = price * quantity
            if available_value <= remaining_usdt:
                buy_quantity = quantity
            else:
                buy_quantity = remaining_usdt / price

            cost = buy_quantity * price
            coin_amount += buy_quantity
            spent_usdt += cost
            remaining_usdt -= cost
            levels_used += 1

            if remaining_usdt <= 0.00000001:
                break

        if spent_usdt < (usdt_amount * 0.999) or coin_amount <= 0:
            return None

        average_price = spent_usdt / coin_amount
        return {
            "coin_amount": coin_amount,
            "spent_usdt": spent_usdt,
            "average_price": average_price,
            "levels_used": levels_used
        }

    # =========================================================
    # SELL ORDERBOOK SIMULATION
    # =========================================================
    def simulate_sell(self, bids, coin_amount):
        remaining_coin = float(coin_amount)
        received_usdt = 0.0
        sold_coin = 0.0
        levels_used = 0

        for level in bids:
            if len(level) < 2:
                continue
            try:
                price = float(level[0])
                quantity = float(level[1])
            except Exception:
                continue
            if price <= 0 or quantity <= 0:
                continue

            sell_quantity = min(remaining_coin, quantity)
            received_usdt += sell_quantity * price
            sold_coin += sell_quantity
            remaining_coin -= sell_quantity
            levels_used += 1

            if remaining_coin <= 0.00000001:
                break

        if sold_coin < (coin_amount * 0.999) or sold_coin <= 0:
            return None

        average_price = received_usdt / sold_coin
        return {
            "received_usdt": received_usdt,
            "average_price": average_price,
            "sold_coin": sold_coin,
            "levels_used": levels_used
        }

    # =========================================================
    # ARBITRAGE PRÜFEN & AUSFÜHREN (Paper)
    # =========================================================
    def execute_arbitrage(self, symbol, buy_ex_name, sell_ex_name,
                          ticker_buy, ticker_sell):
        try:
            ask_buy = ticker_buy.get("ask")
            bid_sell = ticker_sell.get("bid")
            if not ask_buy or not bid_sell:
                return

            ask_buy = float(ask_buy)
            bid_sell = float(bid_sell)
            if ask_buy <= 0 or bid_sell <= 0:
                return

            raw_margin = ((bid_sell - ask_buy) / ask_buy) * 100
            if raw_margin <= 0:
                return

            # Ungültige / extreme Spreads verwerfen
            if raw_margin > self.max_raw_margin_pct:
                print(f"🛑 [{symbol}] Ungültiger Spread +{raw_margin:.3f}% → VERWORFEN")
                self.invalid_spreads += 1
                self.log_chance(symbol, buy_ex_name, sell_ex_name,
                                ask_buy, bid_sell, raw_margin, 0,
                                "INVALID_TICKER_SPREAD")
                return

            fee_buy = self.exchanges[buy_ex_name]["fee"]
            fee_sell = self.exchanges[sell_ex_name]["fee"]
            total_fee_pct = (fee_buy + fee_sell) * 100
            estimated_net = raw_margin - total_fee_pct

            if raw_margin >= 0.05:
                print(
                    f"👀 {symbol} ({buy_ex_name.upper()} -> {sell_ex_name.upper()}): "
                    f"Ticker-Brutto +{raw_margin:.3f}% | geschätzt Netto {estimated_net:+.3f}%"
                )

            if estimated_net < self.min_profit_pct:
                self.rejected_profit += 1
                self.log_chance(symbol, buy_ex_name, sell_ex_name,
                                ask_buy, bid_sell, raw_margin, estimated_net,
                                "TICKER_BELOW_MIN_PROFIT")
                return

            # Kapitalprüfung
            available_balance = self.balances.get(buy_ex_name, 0.0)
            if available_balance < self.amount:
                print(
                    f"💰 [{symbol}] VERWORFEN: Kapital auf {buy_ex_name.upper()} "
                    f"nur ${available_balance:.2f}"
                )
                self.log_chance(symbol, buy_ex_name, sell_ex_name,
                                ask_buy, bid_sell, raw_margin, estimated_net,
                                "INSUFFICIENT_CAPITAL")
                return

            # Orderbooks laden
            buy_ex = self.exchanges[buy_ex_name]["instance"]
            sell_ex = self.exchanges[sell_ex_name]["instance"]

            print(f"🔎 ORDERBOOK-CHECK {symbol} ({buy_ex_name.upper()} -> {sell_ex_name.upper()})")

            ob_buy = buy_ex.fetch_order_book(symbol, limit=self.orderbook_limit)
            ob_sell = sell_ex.fetch_order_book(symbol, limit=self.orderbook_limit)

            if not ob_buy.get("asks") or not ob_sell.get("bids"):
                self.rejected_orderbook += 1
                print(f"❌ [{symbol}] VERWORFEN: Orderbook leer")
                return

            real_buy_price = float(ob_buy["asks"][0][0])
            real_sell_price = float(ob_sell["bids"][0][0])
            if real_buy_price <= 0 or real_sell_price <= 0:
                return

            real_raw_margin = ((real_sell_price - real_buy_price) / real_buy_price) * 100
            if real_raw_margin <= 0 or real_raw_margin > self.max_raw_margin_pct:
                self.rejected_orderbook += 1
                print(f"❌ [{symbol}] VERWORFEN: Orderbook-Spread {real_raw_margin:+.3f}%")
                self.log_chance(symbol, buy_ex_name, sell_ex_name,
                                real_buy_price, real_sell_price, real_raw_margin, 0,
                                "INVALID_ORDERBOOK_SPREAD")
                return

            # Realistischer Buy über mehrere Levels
            buy_result = self.simulate_buy(ob_buy["asks"], self.amount)
            if not buy_result:
                self.rejected_liquidity += 1
                print(f"❌ [{symbol}] VERWORFEN: Nicht genügend BUY-Liquidität für ${self.amount:.2f}")
                self.log_chance(symbol, buy_ex_name, sell_ex_name,
                                real_buy_price, real_sell_price, real_raw_margin, 0,
                                "LOW_BUY_LIQUIDITY")
                return

            coin_amount = buy_result["coin_amount"] * (1 - fee_buy)

            # Realistischer Sell
            sell_result = self.simulate_sell(ob_sell["bids"], coin_amount)
            if not sell_result:
                self.rejected_liquidity += 1
                print(f"❌ [{symbol}] VERWORFEN: Nicht genügend SELL-Liquidität")
                self.log_chance(symbol, buy_ex_name, sell_ex_name,
                                real_buy_price, real_sell_price, real_raw_margin, 0,
                                "LOW_SELL_LIQUIDITY")
                return

            final_usdt = sell_result["received_usdt"] * (1 - fee_sell)
            profit_usdt = final_usdt - self.amount
            real_profit_pct = (profit_usdt / self.amount) * 100

            # Detailausgabe
            print(f"   Ticker-Brutto:     {raw_margin:+.4f}%")
            print(f"   Orderbook-Brutto:  {real_raw_margin:+.4f}%")
            print(f"   Gebühren:          -{total_fee_pct:.4f}%")
            print(f"   Orderbook BUY Ø:   {buy_result['average_price']:.10f}")
            print(f"   Orderbook SELL Ø:  {sell_result['average_price']:.10f}")
            print(f"   BUY-Level benutzt: {buy_result['levels_used']}")
            print(f"   SELL-Level benutzt:{sell_result['levels_used']}")
            print(f"   Tatsächliches Netto: {real_profit_pct:+.4f}%")
            print(f"   Ergebnis:          ${profit_usdt:+.6f}")

            if real_profit_pct < self.min_profit_pct:
                self.rejected_profit += 1
                print(
                    f"❌ [{symbol}] VERWORFEN: Orderbook-Netto {real_profit_pct:+.4f}% "
                    f"< {self.min_profit_pct:.2f}%"
                )
                self.log_chance(symbol, buy_ex_name, sell_ex_name,
                                real_buy_price, real_sell_price, real_raw_margin,
                                real_profit_pct, "ORDERBOOK_BELOW_MIN_PROFIT")
                print("-" * 70)
                return

            if real_profit_pct > self.max_raw_margin_pct:
                self.invalid_spreads += 1
                print(f"🛑 [{symbol}] Unplausibler Netto-Gewinn +{real_profit_pct:.3f}% → VERWORFEN")
                return

            # ===================== PAPER TRADE =====================
            mode_str = "PAPER_TRADING" if self.dry_run else "LIVE_REAL_MONEY"

            self.total_trades += 1
            self.winning_trades += 1
            self.total_profit += profit_usdt
            self.trade_profits.append(profit_usdt)

            self.balances[buy_ex_name] -= self.amount
            self.balances[sell_ex_name] += final_usdt

            print("")
            print("=" * 70)
            print(f"🔥 [PAPER TRADE] {symbol}")
            print(f"{buy_ex_name.upper()} -> {sell_ex_name.upper()}")
            print(f"Einsatz: ${self.amount:,.2f}")
            print(f"BUY Ø:   {buy_result['average_price']:.10f}")
            print(f"SELL Ø:  {sell_result['average_price']:.10f}")
            print(f"Netto:   +{real_profit_pct:.4f}%")
            print(f"Gewinn:  +${profit_usdt:.6f}")
            print(f"Modus:   {mode_str}")
            print("=" * 70)

            # CSV schreiben
            try:
                with open(self.csv_file, "a", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(
                        f,
                        fieldnames=[
                            "timestamp", "symbol", "buy_ex", "sell_ex",
                            "trade_amount", "buy_price", "sell_price",
                            "raw_margin_pct", "real_profit_pct", "profit_usdt",
                            "execution_mode", "status"
                        ]
                    )
                    writer.writerow({
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "symbol": symbol,
                        "buy_ex": buy_ex_name.upper(),
                        "sell_ex": sell_ex_name.upper(),
                        "trade_amount": round(self.amount, 4),
                        "buy_price": round(buy_result["average_price"], 10),
                        "sell_price": round(sell_result["average_price"], 10),
                        "raw_margin_pct": round(real_raw_margin, 5),
                        "real_profit_pct": round(real_profit_pct, 5),
                        "profit_usdt": round(profit_usdt, 6),
                        "execution_mode": mode_str,
                        "status": "PAPER_EXECUTED"
                    })
            except Exception as e:
                print(f"⚠️ CSV-Fehler: {e}")

        except Exception as e:
            print(
                f"⚠️ Fehler bei {symbol} ({buy_ex_name}->{sell_ex_name}): "
                f"{type(e).__name__}: {e}"
            )

    # =========================================================
    # STATISTIK
    # =========================================================
    def print_statistics(self, runtime_seconds):
        end_total = sum(self.balances.values())
        total_return_pct = (
            (end_total - self.starting_total_balance) / self.starting_total_balance
        ) * 100

        if self.trade_profits:
            average_profit = sum(self.trade_profits) / len(self.trade_profits)
            best_trade = max(self.trade_profits)
            worst_trade = min(self.trade_profits)
        else:
            average_profit = best_trade = worst_trade = 0.0

        win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0.0

        print("")
        print("=" * 70)
        print("🏁 PAPER-TEST BEENDET")
        print("=" * 70)
        print(f"💰 Startkapital gesamt: ${self.starting_total_balance:,.2f}")
        print(f"💰 Endkapital gesamt:   ${end_total:,.4f}")
        print(f"📈 Gesamtgewinn:        ${self.total_profit:+.6f}")
        print(f"📊 Rendite:             {total_return_pct:+.4f}%")
        print(f"🔥 Trades:              {self.total_trades}")
        print(f"✅ Gewinntrades:        {self.winning_trades}")
        print(f"❌ Verlusttrades:       {self.losing_trades}")
        print(f"🎯 Trefferquote:        {win_rate:.2f}%")
        print(f"💵 Ø Gewinn/Trade:      ${average_profit:+.6f}")
        print(f"🚀 Bester Trade:        ${best_trade:+.6f}")
        print(f"📉 Schlechtester Trade: ${worst_trade:+.6f}")
        print("")
        for name, bal in self.balances.items():
            print(f"🏦 {name.upper()} USDT: ${bal:,.4f}")
        print("")
        print(f"🛑 Ungültige Spreads:     {self.invalid_spreads}")
        print(f"💧 Liquidität verworfen:  {self.rejected_liquidity}")
        print(f"📚 Orderbook verworfen:   {self.rejected_orderbook}")
        print(f"📉 Gewinnschwelle verworfen: {self.rejected_profit}")
        print("")
        print(f"⏱️ Laufzeit: {runtime_seconds / 60:.2f} Minuten")
        print("=" * 70)

    # =========================================================
    # HAUPTSCHLEIFE
    # =========================================================
    def run_continuous(self, duration_hours=1, delay_seconds=3):
        mode_label = "PAPERHANDEL (SIMULATION)" if self.dry_run else "LIVE TRADING (ECHTGELD)"

        print("")
        print(f"🚀 Starte Trader [{mode_label}]...")
        print(f"💰 Handelsgröße:              ${self.amount:,.2f}")
        print(f"🏦 Startkapital pro Börse:    ${self.starting_balance_per_exchange:,.2f}")
        print(f"💰 Gesamtes Startkapital:     ${self.starting_total_balance:,.2f}")
        print(f"🎯 Mindest-Netto:             {self.min_profit_pct:.2f}%")
        print(f"📚 Orderbook-Level:           {self.orderbook_limit}")
        print(f"🛡️ Max. Bruttomarge:          {self.max_raw_margin_pct:.1f}%")
        print(f"🏦 Aktive Börsen:             {', '.join(ex.upper() for ex in self.exchanges)}")
        print(f"⏱️ Laufzeit:                  {duration_hours * 60:.0f} Minuten | Pause: {delay_seconds}s")
        print("")

        # Märkte laden
        for name, data in list(self.exchanges.items()):
            try:
                data["instance"].load_markets()
                print(f"✅ Märkte geladen für {name.upper()}: {len(data['instance'].markets)} Paare")
            except Exception as e:
                print(f"⚠️ Märkte konnten für {name.upper()} nicht geladen werden: {e}")

        start_time = time.time()
        end_time = start_time + duration_hours * 3600
        cycle = 1

        while time.time() < end_time:
            elapsed_min = int((time.time() - start_time) / 60)
            print("")
            print(f"🔄 Scan-Zyklus {cycle} | Verstrichene Zeit: {elapsed_min} Min.")

            active = list(self.exchanges.keys())

            for i in range(len(active)):
                for j in range(len(active)):
                    if i == j:
                        continue
                    ex1 = active[i]
                    ex2 = active[j]
                    try:
                        t1 = self.exchanges[ex1]["instance"].fetch_tickers()
                        t2 = self.exchanges[ex2]["instance"].fetch_tickers()

                        s1 = {s for s in t1.keys() if s.endswith("/USDT")}
                        s2 = {s for s in t2.keys() if s.endswith("/USDT")}
                        common = s1.intersection(s2)

                        for symbol in common:
                            ticker1 = t1.get(symbol, {})
                            ticker2 = t2.get(symbol, {})
                            self.execute_arbitrage(symbol, ex1, ex2, ticker1, ticker2)

                    except Exception as e:
                        print(f"⚠️ Fehler beim Pair-Fetch ({ex1}-{ex2}): {type(e).__name__}: {e}")

            cycle += 1
            time.sleep(delay_seconds)

        runtime_seconds = time.time() - start_time
        self.print_statistics(runtime_seconds)


# =============================================================
# START – 10 Minuten Paper-Test
# =============================================================
if __name__ == "__main__":
    trader = MultiExchangeTrader(
        amount_per_trade=1000.0,
        starting_balance_per_exchange=1000.0,
        min_profit_pct=0.10,
        dry_run=True                 # Paper-Trading
    )

    trader.run_continuous(
        duration_hours=10 / 60,      # 10 Minuten
        delay_seconds=3              # etwas entspannter bei 3 Börsen
    )
