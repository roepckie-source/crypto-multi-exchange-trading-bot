import time
from datetime import datetime

from market_scanner import get_btc_prices, find_best_opportunity
from paper_trader import PaperTrader

SCAN_INTERVAL = 30

print("🚀 MAIN.PY WURDE GESTARTET", flush=True)

def main():
print("\n" + "=" * 65, flush=True)
print("🚀 CRYPTO MULTI-EXCHANGE TRADING BOT", flush=True)
print("📊 BTC REAL ORDERBOOK ARBITRAGE", flush=True)
print("🤖 PAPER TRADING MODE", flush=True)
print("=" * 65, flush=True)

```
trader = PaperTrader(
    starting_balance=10000.0,
    trade_size=1000.0,
    min_profit_percent=0.10
)

print(f"\n💰 Virtuelles Startkapital: ${trader.starting_balance:,.2f}", flush=True)
print(f"💵 Tradegröße: ${trader.trade_size:,.2f}", flush=True)
print(f"🎯 Mindest-Netto-Gewinn: {trader.min_profit_percent:.2f}%", flush=True)
print(f"⏱️ Scan-Intervall: {SCAN_INTERVAL} Sekunden", flush=True)
print("\n🧪 PAPER TRADING – KEIN ECHTGELD", flush=True)

try:
    while True:
        print("\n" + "=" * 65, flush=True)
        print("🔎 NEUER MARKT-SCAN", flush=True)
        print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), flush=True)
        print("=" * 65, flush=True)

        print("\n🔎 STARTE PREISABFRAGE", flush=True)

        prices = get_btc_prices()

        print(
            f"\n✅ PREISE ERHALTEN: {len(prices)} BÖRSEN",
            flush=True
        )

        if not prices:
            print("❌ KEINE PREISE ERHALTEN", flush=True)
            time.sleep(SCAN_INTERVAL)
            continue

        print("\n🧠 STARTE ORDERBOOK-ANALYSE", flush=True)

        opportunity = find_best_opportunity(prices)

        print("\n✅ ANALYSE ZURÜCKGEKEHRT", flush=True)
        print(
            f"Opportunity vorhanden: {opportunity is not None}",
            flush=True
        )

        if opportunity:
            print("\n🤖 ÜBERGABE AN PAPER TRADER", flush=True)

            try:
                trader.evaluate_trade(opportunity)

            except Exception as e:
                print(
                    f"❌ PAPER-TRADER FEHLER: {type(e).__name__}: {e}",
                    flush=True
                )

        else:
            print("\n⚪ KEINE ARBITRAGE-CHANCE", flush=True)

        print(
            "\n📊 AKTUELLE PAPER-TRADING-STATISTIK",
            flush=True
        )

        try:
            trader.print_statistics()

        except Exception as e:
            print(
                f"❌ STATISTIK-FEHLER: {type(e).__name__}: {e}",
                flush=True
            )

        print(
            f"\n⏳ Nächster Scan in {SCAN_INTERVAL} Sekunden...",
            flush=True
        )

        time.sleep(SCAN_INTERVAL)

except KeyboardInterrupt:
    print("\n🛑 PAPER TRADING MANUELL BEENDET", flush=True)
    trader.print_statistics()

except Exception as e:
    print("\n❌ UNERWARTETER HAUPTFEHLER", flush=True)
    print(f"{type(e).__name__}: {e}", flush=True)
    raise
```

if **name** == "**main**":
main()
