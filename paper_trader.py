class PaperTrader:

    def __init__(
        self,
        starting_balance=10000.0,
        trade_size=1000.0,
        min_profit_percent=0.10
    ):
        self.starting_balance = float(starting_balance)
        self.balance = float(starting_balance)

        self.trade_size = float(trade_size)
        self.min_profit_percent = float(min_profit_percent)

        self.scans = 0
        self.opportunities = 0
        self.accepted_trades = 0
        self.rejected_trades = 0

        self.total_profit = 0.0
        self.winning_trades = 0
        self.losing_trades = 0

        self.best_trade = None
        self.worst_trade = None

    def register_scan(self):
        self.scans += 1

    def evaluate_trade(self, opportunity):

        if not opportunity:
            return False

        self.opportunities += 1

        profit = float(
            opportunity.get("net_profit", 0.0)
        )

        profit_percent = float(
            opportunity.get("net_profit_percent", 0.0)
        )

        buy_exchange = opportunity.get(
            "buy_exchange",
            "unknown"
        )

        sell_exchange = opportunity.get(
            "sell_exchange",
            "unknown"
        )

        trade_size = float(
            opportunity.get(
                "trade_size",
                self.trade_size
            )
        )

        print("\n" + "=" * 65, flush=True)
        print("🤖 PAPER TRADING ENGINE", flush=True)
        print("=" * 65, flush=True)

        print(
            f"Kaufen:       {buy_exchange.upper()}",
            flush=True
        )

        print(
            f"Verkaufen:    {sell_exchange.upper()}",
            flush=True
        )

        print(
            f"Tradegröße:   ${trade_size:,.2f}",
            flush=True
        )

        print(
            f"Netto:        {profit_percent:.4f}%",
            flush=True
        )

        print(
            f"Netto-Gewinn: ${profit:,.4f}",
            flush=True
        )

        if profit_percent < self.min_profit_percent:

            self.rejected_trades += 1

            print(
                "\n🔴 PAPER TRADE ABGELEHNT",
                flush=True
            )

            print(
                f"Grund: Netto-Gewinn unter "
                f"{self.min_profit_percent:.2f}%",
                flush=True
            )

            return False

        if trade_size > self.balance:

            self.rejected_trades += 1

            print(
                "\n🔴 PAPER TRADE ABGELEHNT",
                flush=True
            )

            print(
                "Grund: Nicht genügend virtuelles Kapital",
                flush=True
            )

            return False

        self.accepted_trades += 1

        self.balance += profit
        self.total_profit += profit

        if profit > 0:
            self.winning_trades += 1

        elif profit < 0:
            self.losing_trades += 1

        trade = {
            "profit": profit,
            "profit_percent": profit_percent,
            "buy_exchange": buy_exchange,
            "sell_exchange": sell_exchange,
            "trade_size": trade_size,
        }

        if (
            self.best_trade is None
            or profit > self.best_trade["profit"]
        ):
            self.best_trade = trade.copy()

        if (
            self.worst_trade is None
            or profit < self.worst_trade["profit"]
        ):
            self.worst_trade = trade.copy()

        print(
            "\n🟢 PAPER TRADE AUSGEFÜHRT",
            flush=True
        )

        print(
            f"Gewinn:       ${profit:,.4f}",
            flush=True
        )

        print(
            f"Neues Kapital: ${self.balance:,.2f}",
            flush=True
        )

        print("=" * 65, flush=True)

        return True

    def print_statistics(self):

        if self.accepted_trades > 0:
            win_rate = (
                self.winning_trades
                / self.accepted_trades
            ) * 100
        else:
            win_rate = 0.0

        return_percent = (
            (
                self.balance
                - self.starting_balance
            )
            / self.starting_balance
        ) * 100

        print("\n" + "=" * 65, flush=True)
        print("📊 PAPER TRADING STATISTIK", flush=True)
        print("=" * 65, flush=True)

        print(
            f"Scans:              {self.scans}",
            flush=True
        )

        print(
            f"Arbitrage-Chancen:  {self.opportunities}",
            flush=True
        )

        print(
            f"Paper Trades:       {self.accepted_trades}",
            flush=True
        )

        print(
            f"Abgelehnt:          {self.rejected_trades}",
            flush=True
        )

        print(
            f"Gewinner:           {self.winning_trades}",
            flush=True
        )

        print(
            f"Verlierer:          {self.losing_trades}",
            flush=True
        )

        print(
            f"Trefferquote:       {win_rate:.2f}%",
            flush=True
        )

        print("-" * 65, flush=True)

        print(
            f"Startkapital:       ${self.starting_balance:,.2f}",
            flush=True
        )

        print(
            f"Aktuelles Kapital:  ${self.balance:,.2f}",
            flush=True
        )

        print(
            f"Gesamtgewinn:       ${self.total_profit:,.4f}",
            flush=True
        )

        print(
            f"Rendite:            {return_percent:.4f}%",
            flush=True
        )

        if self.best_trade:
            print("\n🏆 BESTER PAPER TRADE", flush=True)
            print(
                f"Gewinn:             ${self.best_trade['profit']:,.4f}",
                flush=True
            )
            print(
                f"Netto:              {self.best_trade['profit_percent']:.4f}%",
                flush=True
            )
            print(
                f"BUY:                {self.best_trade['buy_exchange'].upper()}",
                flush=True
            )
            print(
                f"SELL:               {self.best_trade['sell_exchange'].upper()}",
                flush=True
            )

        if self.worst_trade:
            print("\n📉 SCHLECHTESTER PAPER TRADE", flush=True)
            print(
                f"Gewinn:             ${self.worst_trade['profit']:,.4f}",
                flush=True
            )
            print(
                f"Netto:              {self.worst_trade['profit_percent']:.4f}%",
                flush=True
            )
            print(
                f"BUY:                {self.worst_trade['buy_exchange'].upper()}",
                flush=True
            )
            print(
                f"SELL:               {self.worst_trade['sell_exchange'].upper()}",
                flush=True
            )

        print("=" * 65, flush=True)
