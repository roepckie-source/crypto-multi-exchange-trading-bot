import json
import os
from datetime import datetime


STATE_FILE = "paper_state.json"


class PaperTrader:

    def __init__(
        self,
        starting_balance=10000.0,
        trade_size=1000.0,
        min_profit_percent=0.10
    ):

        self.starting_balance = starting_balance
        self.trade_size = trade_size
        self.min_profit_percent = min_profit_percent

        self.balance = starting_balance
        self.total_profit = 0.0
        self.total_trades = 0
        self.profitable_trades = 0
        self.rejected_trades = 0
        self.history = []

        self.load_state()

    def load_state(self):

        if not os.path.exists(STATE_FILE):
            return

        try:
            with open(
                STATE_FILE,
                "r",
                encoding="utf-8"
            ) as file:

                state = json.load(file)

            self.balance = state.get(
                "balance",
                self.starting_balance
            )

            self.total_profit = state.get(
                "total_profit",
                0.0
            )

            self.total_trades = state.get(
                "total_trades",
                0
            )

            self.profitable_trades = state.get(
                "profitable_trades",
                0
            )

            self.rejected_trades = state.get(
                "rejected_trades",
                0
            )

            self.history = state.get(
                "history",
                []
            )

            print(
                f"💾 Paper-Trading-Status geladen: "
                f"${self.balance:,.2f}"
            )

        except Exception as e:

            print(
                f"⚠️ State konnte nicht geladen werden: {e}"
            )

    def save_state(self):

        state = {
            "balance": self.balance,
            "starting_balance": self.starting_balance,
            "total_profit": self.total_profit,
            "total_trades": self.total_trades,
            "profitable_trades": self.profitable_trades,
            "rejected_trades": self.rejected_trades,
            "history": self.history[-1000:]
        }

        with open(
            STATE_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                state,
                file,
                indent=2
            )

    def evaluate_trade(self, opportunity):

        net_profit_percent = (
            opportunity["net_profit_percent"]
        )

        print("\n" + "=" * 65)
        print("🤖 PAPER TRADING ENGINE")
        print("=" * 65)

        print(
            f"Virtuelles Kapital: "
            f"${self.balance:,.2f}"
        )

        print(
            f"Tradegröße: "
            f"${self.trade_size:,.2f}"
        )

        print(
            f"Netto-Chance: "
            f"{net_profit_percent:.4f}%"
        )

        if net_profit_percent < self.min_profit_percent:

            self.rejected_trades += 1
            self.save_state()

            print(
                "\n🔴 PAPER TRADE ABGELEHNT"
            )

            print(
                "Grund: Netto-Gewinn "
                "unter Mindestgrenze"
            )

            return False

        if self.balance < self.trade_size:

            print(
                "\n🔴 PAPER TRADE ABGELEHNT"
            )

            print(
                "Grund: Virtuelles Kapital "
                "nicht ausreichend"
            )

            return False

        profit = (
            self.trade_size
            * net_profit_percent
            / 100
        )

        self.balance += profit
        self.total_profit += profit

        self.total_trades += 1
        self.profitable_trades += 1

        trade = {
            "time": datetime.utcnow().isoformat(),
            "buy_exchange": (
                opportunity["buy_exchange"]
            ),
            "sell_exchange": (
                opportunity["sell_exchange"]
            ),
            "buy_price": (
                opportunity["buy_price"]
            ),
            "sell_price": (
                opportunity["sell_price"]
            ),
            "net_profit_percent": (
                net_profit_percent
            ),
            "profit": profit,
            "balance_after": self.balance
        }

        self.history.append(trade)

        self.save_state()

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
            f"Netto: "
            f"{net_profit_percent:.4f}%"
        )

        print(
            f"Gewinn: "
            f"${profit:,.2f}"
        )

        print(
            f"Neue Balance: "
            f"${self.balance:,.2f}"
        )

        print("=" * 65)

        return True

    def print_statistics(self):

        print("\n📊 PAPER TRADING STATISTIK")
        print("=" * 65)

        profit_percent = (
            (
                self.balance
                - self.starting_balance
            )
            / self.starting_balance
        ) * 100

        print(
            f"Startkapital:       "
            f"${self.starting_balance:,.2f}"
        )

        print(
            f"Aktuelles Kapital:  "
            f"${self.balance:,.2f}"
        )

        print(
            f"Gesamtgewinn:       "
            f"${self.total_profit:,.2f}"
        )

        print(
            f"Rendite:            "
            f"{profit_percent:.4f}%"
        )

        print(
            f"Ausgeführte Trades: "
            f"{self.total_trades}"
        )

        print(
            f"Abgelehnte Chancen: "
            f"{self.rejected_trades}"
        )

        if self.total_trades > 0:

            win_rate = (
                self.profitable_trades
                / self.total_trades
            ) * 100

            print(
                f"Trefferquote:       "
                f"{win_rate:.2f}%"
            )

        print("=" * 65)
