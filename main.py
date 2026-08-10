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

            # --------------------------------------------------
            # PREISE ABFRAGEN
            # --------------------------------------------------

            print(
                "📡 Rufe get_btc_prices() auf...",
                flush=True
            )

            prices = get_btc_prices()

            print(
                f"✅ get_btc_prices() beendet: "
                f"{len(prices)} Börsen",
                flush=True
            )

            print(
                f"📦 Preise: {prices}",
                flush=True
            )

            if not prices:

                print(
                    "❌ KEINE PREISE ERHALTEN",
                    flush=True
                )

            else:

                print(
                    "\n✅ PREISE ERHALTEN",
                    flush=True
                )

                # --------------------------------------------------
                # ORDERBOOK-ANALYSE
                # --------------------------------------------------

                print(
                    "\n🧠 Starte echte Orderbuch-Analyse...",
                    flush=True
                )

                opportunity = find_best_opportunity(
                    prices
                )

                print(
                    "\n✅ Orderbuch-Analyse beendet",
                    flush=True
                )

                # --------------------------------------------------
                # OPPORTUNITY
                # --------------------------------------------------

                if opportunity:

                    print(
                        "\n📊 OPPORTUNITY",
                        flush=True
                    )

                    print(
                        opportunity,
                        flush=True
                    )

                    # --------------------------------------------------
                    # PAPER TRADING
                    # --------------------------------------------------

                    print(
                        "\n🤖 Übergabe an Paper Trader...",
                        flush=True
                    )

                    trader.evaluate_trade(
                        opportunity
                    )

                else:

                    print(
                        "\n⚪ KEINE AUSWERTBARE OPPORTUNITY",
                        flush=True
                    )

        except Exception as e:

            print(
                "\n❌ FEHLER IM SCAN",
                flush=True
            )

            print(
                f"Fehlertyp: {type(e).__name__}",
                flush=True
            )

            print(
                f"Fehlermeldung: {e}",
                flush=True
            )

        # --------------------------------------------------
        # STATISTIK
        # --------------------------------------------------

        print(
            "\n📊 PAPER TRADING STATISTIK",
            flush=True
        )

        trader.print_statistics()

        # --------------------------------------------------
        # WARTEN
        # --------------------------------------------------

        print(
            f"\n⏳ Nächster Scan in "
            f"{SCAN_INTERVAL} Sekunden...",
            flush=True
        )

        time.sleep(
            SCAN_INTERVAL
        )


if __name__ == "__main__":
    main()
