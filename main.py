from live_trader import MultiExchangeTrader


if __name__ == "__main__":
    trader = MultiExchangeTrader(
        amount_per_trade=10.0,
        min_profit_pct=0.10,
        dry_run=True
    )

    trader.run_continuous(
        duration_hours=1,
        delay_seconds=2
    )
