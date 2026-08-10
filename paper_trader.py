from datetime import datetime


class PaperTrader:

    def __init__(
        self,
        starting_balance=10000.0,
        trade_size=1000.0,
        min_profit_percent=0.10
    ):

        self.balance = (
            starting_balance
        )

        self.starting_balance = (
            starting_balance
        )

        self.trade_size = (
            trade_size
        )

        self.min_profit_percent = (
            min_profit_percent
        )

        self.trades = 0

        self.profitable_trades = 0

        self.total_profit = 0.0

    def evaluate_trade(
        self,
        opportunity
    ):

        net_profit_percent = (
            opportunity[
                "net_profit_percent"
            ]
        )

        print(
            "\n"
            + "=" * 65
        )

        print(
            "🤖 PAPER TRADING ENGINE"
        )

        print(
            "=" * 65
        )

        print(
            f"Virtuelles Kapital: "
            f"${self.balance:,.2f}"
        )

        print(
            f"Tradegröße: "
            f"${self.trade_size:,.2f}"
        )

        print(
            f"Mindestgewinn: "
            f"{self.min_profit_percent:.3f}%"
        )

        print(
            f"\nBerechneter Nettoertrag: "
            f"{net_profit_percent:.4f}%"
        )

        # Kein Trade unterhalb
        # unserer Mindestprofitabilität.

        if (
            net_profit_percent
            < self.min_profit_percent
        ):

            print(
                "\n🔴 PAPER TRADE ABGELEHNT"
            )

            print(
                "Grund: Netto-Gewinn "
                "unter Mindestgrenze"
            )

            return False

        profit = (
            self.trade_size
            * net_profit_percent
            / 100
        )

        self.balance += profit

        self.total_profit += profit

        self.trades += 1

        self.profitable_trades += 1

        print(
            "\n🟢 PAPER TRADE AUSGEFÜHRT"
        )

        print(
            f"Kaufen: "
            f"{opportunity['buy_exchange'].upper()}"
        )

        print(
            f"Verkaufen: "
            f"{opportunity['sell_exchange'].upper()}"
        )

        print(
            f"Tradegröße: "
            f"${self.trade_size:,.2f}"
        )

        print(
            f"Gewinn: "
            f"${profit:,.2f}"
        )

        print(
            f"Neue Balance: "
            f"${self.balance:,.2f}"
        )

        print(
            "=" * 65
        )

        return True

    def print_statistics(self):

        print(
            "\n📊 PAPER TRADING STATISTIK"
        )

        print(
            "=" * 65
        )

        print(
            f"Startkapital: "
            f"${self.starting_balance:,.2f}"
        )

        print(
            f"Aktuelles Kapital: "
            f"${self.balance:,.2f}"
        )

        print(
            f"Gesamtgewinn: "
            f"${self.total_profit:,.2f}"
        )

        print(
            f"Trades: "
            f"{self.trades}"
        )

        if self.trades > 0:

            win_rate = (
                self.profitable_trades
                / self.trades
            ) * 100

            print(
                f"Profit Rate: "
                f"{win_rate:.2f}%"
            )

        print(
            f"Zeit: "
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        print(
            "=" * 65
        )
