import time
from market_scanner import get_btc_prices, find_best_opportunity
from paper_trader import PaperTrader

SCAN_INTERVAL = 30

def main():
print("🚀 START", flush=True)

```
trader = PaperTrader(
    starting_balance=10000.0,
    trade_size=1000.0,
    min_profit_percent=0.10
)

while True:
    print("🔎 SCAN", flush=True)

    try:
        prices = get_btc_prices()

        if prices:
            opportunity = find_best_opportunity(prices)

            if opportunity:
                trader.evaluate_trade(opportunity)

    except Exception as e:
        print(f"❌ FEHLER: {e}", flush=True)

    time.sleep(SCAN_INTERVAL)
```

if **name** == "**main**":
main()
