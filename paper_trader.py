class PaperTrader:
    def __init__(self, starting_balance=100.0, min_profit_percent=0.01):
        self.starting_balance = float(starting_balance)
        self.balance = float(starting_balance)
        self.min_profit_percent = float(min_profit_percent)
        self.scans = 0
        self.opportunities = 0
        self.accepted_trades = 0
        self.rejected_trades = 0
        self.total_profit = 0.0

    def register_scan(self):
        self.scans += 1

    def evaluate_trade(self, opportunity):
        if not opportunity: return False
        self.opportunities += 1

        profit = float(opportunity.get("net_profit", 0.0))
        profit_percent = float(opportunity.get("net_profit_percent", 0.0))
        coin = opportunity.get("coin", "UNKNOWN")

        print("\n" + "=" * 65, flush=True)
        print("🤖 BITRUE TRIANGULAR ENGINE", flush=True)
        print("=" * 65, flush=True)
        print(f"Dreieck-Route: USDT ➔ {coin} ➔ BTC ➔ USDT", flush=True)
        print(f"Einsatz:        ${opportunity['trade_size']:,.2f}", flush=True)
        print(f"Netto Rendite: {profit_percent:+.4f}%", flush=True)
        print(f"Netto Gewinn:  ${profit:,.4f}", flush=True)

        if profit_percent < self.min_profit_percent:
            self.rejected_trades += 1
            print(f"🔴 ABGELEHNT: Gewinn unter {self.min_profit_percent}%", flush=True)
            return False

        self.accepted_trades += 1
        self.balance += profit
        self.total_profit += profit

        print(f"🟢 GEWINNBRINGENDES DREIECK AUSGEFÜHRT!")
        print(f"Neues Kapital: ${self.balance:,.2f}", flush=True)
        print("=" * 65, flush=True)
        return True

    def print_statistics(self):
        return_percent = ((self.balance - self.starting_balance) / self.starting_balance) * 100
        print("\n" + "=" * 65, flush=True)
        print("📊 BITRUE TRADING STATISTIK", flush=True)
        print("=" * 65, flush=True)
        print(f"Scans: {self.scans} | Trades ausgeführt: {self.accepted_trades} | Abgelehnt: {self.rejected_trades}", flush=True)
        print(f"Startkapital: ${self.starting_balance:,.2f} | Aktuelles Kapital: ${self.balance:,.2f}", flush=True)
        print(f"Rendite: {return_percent:+.4f}%", flush=True)
        print("=" * 65, flush=True)
