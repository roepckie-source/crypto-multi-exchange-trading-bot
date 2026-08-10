import time

from market_scanner import get_btc_prices, find_best_opportunity
from paper_trader import PaperTrader

SCAN_INTERVAL = 30

def main():
print("🚀 START BTC SCANNER", flush=True)
print("🤖 PAPER TRADING AKTIV", flush=True)

```
trader = PaperTrader(
    starting_balance=10000.0,
    trade_size=1000.0,
    min_profit_percent=0.10
)

while True:
    print("\n" + "=" * 65, flush=True)
    print("🔎 NEUER SCAN", flush=True)
    print("=" * 65, flush=True)

    try:
        print("📡 Rufe Börsenkurse ab...", flush=True)

        prices = get_btc_prices()

        print(
            f"✅ PREISE ERHALTEN: {len(prices)} Börsen",
            flush=True
        )

        if not prices:
            print("❌ KEINE PREISE ERHALTEN", flush=True)

        else:
            print(
                "\n🧠 STARTE ORDERBOOK-ANALYSE",
                flush=True
            )

            opportunity = find_best_opportunity(prices)

            if opportunity:
                print(
                    "\n📊 OPPORTUNITY",
                    flush=True
                )

                print(
                    opportunity,
                    flush=True
                )

                trader.evaluate_trade(opportunity)

            else:
                print(
                    "\n⚪ KEINE OPPORTUNITY",
                    flush=True
                )

    except Exception as e:
        print(
            "\n❌ FEHLER IM SCAN",
            flush=True
        )

        print(
            f"{type(e).__name__}: {e}",
            flush=True
        )

    print(
        "\n📊 PAPER TRADING STATISTIK",
        flush=True
    )

    try:
        trader.print_statistics()

    except Exception as e:
        print(
            f"⚠️ Statistik-Fehler: {e}",
            flush=True
        )

    print(
        f"\n⏳ Nächster Scan in "
        f"{SCAN_INTERVAL} Sekunden...",
        flush=True
    )

    time.sleep(SCAN_INTERVAL)
```

if **name** == "**main**":
main()
