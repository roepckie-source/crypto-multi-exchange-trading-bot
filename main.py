import time

from market_scanner import (
    get_btc_prices,
    find_best_opportunity
)

from paper_trader import PaperTrader


SCAN_INTERVAL = 30


def main():

    print("🚀 START BTC SCANNER", flush=True)
    print("🤖 PAPER TRADING AKTIV", flush=True)

    trader = PaperTrader(
        starting_balance=10000.0,
        trade_size=1000.0,
        min_profit_percent=0.10
    )

    while True:

        print("\n" + "=" * 65, flush=True)
        print("🔎 NEUER SCAN", flush=True)
        print("=" * 65, flush=True)

        trader.register_scan()

        try:

            prices = get_btc_prices()

            if not prices:

                print(
                    "❌ Keine Preise erhalten",
                    flush=True
                )

            else:

                print(
                    "\n✅ PREISE ERHALTEN",
                    flush=True
                )

                opportunity = find_best_opportunity(
                    prices
                )

                if opportunity:

                    print(
                        "\n📊 OPPORTUNITY",
                        flush=True
                    )

                    print(
                        opportunity,
                        flush=True
                    )

                    trader.evaluate_trade(
                        opportunity
                    )

                else:

                    print(
                        "\n⚪ KEINE OPPORTUNITY",
                        flush=True
                    )

        except Exception as e:

            print(
                f"\n❌ FEHLER: "
                f"{type(e).__name__}: {e}",
                flush=True
            )

        print(
            "\n📊 PAPER TRADING STATISTIK",
            flush=True
        )

        trader.print_statistics()

        print(
            f"\n⏳ Nächster Scan "
            f"in {SCAN_INTERVAL} Sekunden...",
            flush=True
        )

        time.sleep(
            SCAN_INTERVAL
        )


if __name__ == "__main__":
    main()
