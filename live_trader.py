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
        self.amount = float(amount_per_trade)
        self.starting_balance_per_exchange = float(starting_balance_per_exchange)
        self.min_profit_pct = float(min_profit_pct)
        self.max_raw_margin_pct = 5.0
        self.dry_run = dry_run
        self.orderbook_limit = 20
        self.default_fee = 0.001

        # Kapitalverteilung auf alle 3 Börsen
        self.balances = {
            "okx": self.starting_balance_per_exchange,
            "kucoin": self.starting_balance_per_exchange,
            "bitrue": self.starting_balance_per_exchange,
        }
        self.starting_total_balance = (
            self.starting_balance_per_exchange * len(self.balances)
        )

        self.exchanges = {}

        # Initialisierung von OKX, KuCoin und Bitrue
        for ex_name, ex_class in [
            ("okx", ccxt.okx),
            ("kucoin", ccxt.kucoin),
            ("bitrue", ccxt.bitrue),
        ]:
            try:
                config = {
                    "enableRateLimit": True,
                    "timeout": 10000,
                    "options": {"defaultType": "spot"},
                }
                api_key = os.getenv(f"{ex_name.upper()}_API_KEY", "")
                if api_key and not dry_run:
                    config.update({
                        "apiKey": api_key,
                        "secret": os.getenv(f"{ex_name.upper()}_API_SECRET", ""),
                        "password": os.getenv(f"{ex_name.upper()}_PASSPHRASE", ""),
                    })
                instance = ex_class(config)
                self.exchanges[ex_name] = {"instance": instance, "fee": self.default_fee}
            except Exception as e:
                print(f"⚠️ Fehler beim Laden von {ex_name.upper()}: {e}")

    # ... Rest des Trader-Codes (execute_arbitrage, run_continuous, etc.) ...

if __name__ == "__main__":
    trader = MultiExchangeTrader(
        amount_per_trade=1000.0,
        starting_balance_per_exchange=1000.0,
        min_profit_pct=0.10,
        dry_run=True,
    )

    # Bot exakt 10 Minuten laufen lassen (10 / 60 Std.)
    trader.run_continuous(
        duration_hours=10 / 60,
        delay_seconds=3
    )
