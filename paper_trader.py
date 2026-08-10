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

        print("\n" + "=" * 65)
        print("🤖 PAPER TRADING ENGINE")
        print("=" * 65)

        print(
            f"Kaufen:       {buy_exchange.upper()}"
        )

        print(
            f"Verkaufen:    {sell_exchange.upper()}"
        )

        print(
            f"Tradegröße:   ${trade_size:,.2f}"
        )

        print(
            f"Netto:        {profit_percent:.4f}%"
        )

        print(
            f"Netto-Gewinn: ${profit:,.4f}"
        )

        # --------------------------------------------------
        # Prüfen, ob der Trade profitabel genug ist
        # --------------------------------------------------

        if profit_percent < self.min_profit_percent:

            self.rejected_trades += 1

            print(
                "\n🔴 PAPER TRADE ABGELEHNT"
            )

            print(
                f"Grund: Netto-Gewinn "
                f"unter {self.min_profit_percent:.2f}%"
            )

            return False

        # --------------------------------------------------
        # Kapital prüfen
        # --------------------------------------------------

        if trade_size > self.balance:

            self.rejected_trades += 1

            print(
                "\n🔴 PAPER TRADE ABGELEHNT"
            )

            print(
                "Grund: Nicht genügend "
                "virtuelles Kapital"
            )

            return False

        # --------------------------------------------------
        # Paper Trade ausführen
        # --------------------------------------------------

        self.accepted_trades += 1

        self.balance += profit
        self.total_profit += profit

        if profit > 0:

            self.winning_trades += 1

        elif profit < 0:

            self.losing_trades += 1

        # --------------------------------------------------
        # Bester Trade
        # --------------------------------------------------

        if (
            self.best_trade is None
            or profit > self.best_trade["profit"]
        ):

            self.best_trade = {
                "profit": profit,
                "profit_percent": profit_percent,
                "buy_exchange": buy_exchange,
                "sell_exchange": sell_exchange,
                "trade_size": trade_size,
            }

        # --------------------------------------------------
        # Schlechtester Trade
        # --------------------------------------------------

        if (
            self.worst_trade is None
            or profit < self.worst_trade["profit"]
        ):

            self.worst_trade = {
                "profit": profit,
                "profit_percent": profit_percent,
                "buy_exchange": buy_exchange,
                "sell_exchange": sell_exchange,
                "trade_size": trade_size,
            }

        print(
            "\n🟢 PAPER TRADE AUSGEFÜHRT"
        )

        print(
            f"Gewinn:       ${profit:,.4f}"
        )

        print(
            f"Neues Kapital: ${self.balance:,.2f}"
        )

        print("=" * 65)

        return True

    def register_scan(self):

        self.scans += 1

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

        print("\n" + "=" * 65)
        print("📊 PAPER TRADING STATISTIK")
        print("=" * 65)

        print(
            f"Scans:              {self.scans}"
        )

        print(
            f"Arbitrage-Chancen:  {self.opportunities}"
        )

        print(
            f"Paper Trades:       {self.accepted_trades}"
        )

        print(
            f"Abgelehnt:          {self.rejected_trades}"
        )

        print(
            f"Gewinner:           {self.winning_trades}"
        )

        print(
            f"Verlierer:          {self.losing_trades}"
        )

        print(
            f"Trefferquote:       {win_rate:.2f}%"
        )

        print("-" * 65)

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
            f"${self.total_profit:,.4f}"
        )

        print(
            f"Rendite:            "
            f"{return_percent:.4f}%"
        )

        # --------------------------------------------------
        # Bester Trade
        # --------------------------------------------------

        if self.best_trade:

            print("\n🏆 BESTER PAPER TRADE")

            print(
                f"Gewinn:             "
                f"${self.best_trade['profit']:,.4f}"
            )

            print(
                f"Netto:              "
                f"{self.best_trade['profit_percent']:.4f}%"
            )

            print(
                f"BUY:                "
                f"{self.best_trade['buy_exchange'].upper()}"
            )

            print(
                f"SELL:               "
                f"{self.best_trade['sell_exchange'].upper()}"
            )

        # --------------------------------------------------
        # Schlechtester Trade
        # --------------------------------------------------

        if self.worst_trade:

            print("\n📉 SCHLECHTESTER PAPER TRADE")

            print(
                f"Gewinn:             "
                f"${self.worst_trade['profit']:,.4f}"
            )

            print(
                f"Netto:              "
                f"{self.worst_trade['profit_percent']:.4f}%"
            )

            print(
                f"BUY:                "
                f"{self.worst_trade['buy_exchange'].upper()}"
            )

            print(
                f"SELL:               "
                f"{self.worst_trade['sell_exchange'].upper()}"
            )

        print("=" * 65)
```

Und in deiner **`main.py`** ergänzen wir innerhalb der `while True:`-Schleife direkt nach:

```python
print("🔎 SCAN", flush=True)
```

diese Zeile:

```python
trader.register_scan()
```

Danach läuft jeder Scan in etwa so:

```text
🔎 SCAN

Preise...
Orderbücher...
210 Berechnungen...

🔴 NICHT PROFITABEL

📊 PAPER TRADING STATISTIK
Scans:              25
Arbitrage-Chancen:  25
Paper Trades:       0
Abgelehnt:          25

Startkapital:       $10,000.00
Aktuelles Kapital:  $10,000.00
Gesamtgewinn:       $0.0000
Rendite:            0.0000%
```

Das Entscheidende: **Wir lassen den Bot jetzt erst einmal laufen und sammeln echte Daten.** Keine echten Orders, kein Risiko.
