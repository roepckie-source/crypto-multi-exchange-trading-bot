class PaperTrader:

```
def __init__(
    self,
    starting_balance=10000.0,
    trade_size=1000.0,
    min_profit_percent=0.10
):
    self.starting_balance = starting_balance
    self.balance = starting_balance
    self.trade_size = trade_size
    self.min_profit_percent = min_profit_percent

    self.total_trades = 0
    self.profitable_trades = 0
    self.rejected_trades = 0
    self.total_profit = 0.0

def evaluate_trade(self, opportunity):

    print("\n🤖 PAPER TRADING ENGINE", flush=True)

    if not opportunity:
        print(
            "⚪ Keine Opportunity vorhanden",
            flush=True
        )
        return False

    net_profit_percent = opportunity.get(
        "net_profit_percent",
        -999
    )

    net_profit = opportunity.get(
        "net_profit",
        0
    )

    buy_exchange = opportunity.get(
        "buy_exchange",
        "unknown"
    )

    sell_exchange = opportunity.get(
        "sell_exchange",
        "unknown"
    )

    print(
        f"📥 Kaufen: {buy_exchange.upper()}",
        flush=True
    )

    print(
        f"📤 Verkaufen: {sell_exchange.upper()}",
        flush=True
    )

    print(
        f"📊 Netto: {net_profit_percent:.4f}%",
        flush=True
    )

    print(
        f"💰 Erwarteter Gewinn: ${net_profit:.4f}",
        flush=True
    )

    if net_profit_percent < self.min_profit_percent:

        self.rejected_trades += 1

        print(
            "\n🔴 PAPER TRADE ABGELEHNT",
            flush=True
        )

        print(
            f"Grund: Netto unter "
            f"{self.min_profit_percent:.2f}%",
            flush=True
        )

        return False

    if self.trade_size > self.balance:

        print(
            "\n🔴 PAPER TRADE ABGELEHNT",
            flush=True
        )

        print(
            "Grund: Nicht genügend virtuelles Kapital",
            flush=True
        )

        return False

    self.balance += net_profit

    self.total_profit += net_profit

    self.total_trades += 1
    self.profitable_trades += 1

    print(
        "\n🟢 PAPER TRADE AUSGEFÜHRT",
        flush=True
    )

    print(
        f"💵 Gewinn: ${net_profit:.4f}",
        flush=True
    )

    print(
        f"💰 Neues Kapital: ${self.balance:,.2f}",
        flush=True
    )

    return True

def print_statistics(self):

    print("\n" + "=" * 65, flush=True)

    print(
        "📊 PAPER TRADING STATISTIK",
        flush=True
    )

    print("=" * 65, flush=True)

    print(
        f"Startkapital:      ${self.starting_balance:,.2f}",
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
        f"Trades:             {self.total_trades}",
        flush=True
    )

    print(
        f"Profitable Trades:  {self.profitable_trades}",
        flush=True
    )

    print(
        f"Abgelehnte Trades:  {self.rejected_trades}",
        flush=True
    )

    if self.starting_balance > 0:

        performance = (
            self.total_profit
            / self.starting_balance
        ) * 100

        print(
            f"Performance:        {performance:.4f}%",
            flush=True
        )

    print("=" * 65, flush=True)
```
