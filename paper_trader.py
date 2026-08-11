class PaperTrader:
    def __init__(self, starting_balance=10000.0, min_profit_percent=0.10):
        self.starting_balance = float(starting_balance)
        self.balance = float(starting_balance)
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
        if not opportunity: return False
        self.opportunities += 1

        profit = float(opportunity.get("net_profit", 0.0))
        profit_percent = float(opportunity.get("net_profit_percent", 0.0))
        buy_exchange = opportunity.get("buy_exchange", "unknown")
        sell_exchange = opportunity.get("sell_exchange", "unknown")
        trade_size = float(opportunity.get("trade_size", 100.0))

        print("\n" + "=" * 65, flush=True)
        print("🤖 PAPER TRADING ENGINE", flush=True)
        print("=" * 65, flush=True)
        print(f"Kaufen:       {buy_exchange.upper()}", flush=True)
        print(f"Verkaufen:    {sell_exchange.upper()}", flush=True)
        print(f"Tradegröße:   ${trade_size:,.2f}", flush=True)
        print(f"Netto:        {profit_percent:.4f}%", flush=True)
        print(f"Netto-Gewinn: ${profit:,.4f}", flush=True)

        if profit_percent < self.min_profit_percent:
            self.rejected_trades += 1
            print(f"\n🔴 PAPER TRADE ABGELEHNT\nGrund: Netto-Gewinn unter {self.min_profit_percent:.2f}%", flush=True)
            return False

        if trade_size > self.balance:
            self.rejected_trades += 1
            print("\n🔴 PAPER TRADE ABGELEHNT\nGrund: Nicht genügend virtuelles Kapital", flush=True)
            return False

        # Trade ausführen und Kapital anpassen
        self.accepted_trades += 1
        self.balance += profit
        self.total_profit += profit

        if profit > 0: self.winning_trades += 1
        elif profit < 0: self.losing_trades += 1

        trade = {
            "profit": profit,
            "profit_percent": profit_percent,
            "buy_exchange": buy_exchange,
            "sell_exchange": sell_exchange,
            "trade_size": trade_size,
        }

        if self.best_trade is None or profit > self.best_trade["profit"]:
            self.best_trade = trade.copy()
        if self.worst_trade is None or profit < self.worst_trade["profit"]:
            self.worst_trade = trade.copy()

        print(f"\n🟢 PAPER TRADE AUSGEFÜHRT\nGewinn:       ${profit:,.4f}\nNeues Kapital: ${self.balance:,.2f}", flush=True)
        print("=" * 65, flush=True)
        return True

    def print_statistics(self):
        win_rate = (self.winning_trades / self.accepted_trades * 100) if self.accepted_trades > 0 else 0.0
        return_percent = ((self.balance - self.starting_balance) / self.starting_balance) * 100

        print("\n" + "=" * 65, flush=True)
        print("📊 PAPIERHANDELSSTATISTIK", flush=True)
        print("=" * 65, flush=True)
        print(f"Scans:              {self.scans}\nArbitrage-Chancen:  {self.opportunities}\nPapiertrades:       {self.accepted_trades}\nAbgelehnt:          {self.rejected_trades}", flush=True)
        print(f"Gewinner:           {self.winning_trades}\nVerlierer:          {self.losing_trades}\nTrefferquote:       {win_rate:.2f}%", flush=True)
        print("-" * 65, flush=True)
        print(f"Startkapital:       ${self.starting_balance:,.2f}\nAktuelles Kapital:  ${self.balance:,.2f}\nGesamtgewinn:       ${self.total_profit:,.4f}\nRendite:            {return_percent:.4f}%", flush=True)
        print("=" * 65, flush=True)
