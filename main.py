import time

from market_scanner import (
    get_btc_prices,
    find_best_opportunity
)

from paper_trader import PaperTrader


SCAN_INTERVAL = 30


def main():

    print("\n" + "=" * 65)
    print("🚀 CRYPTO MULTI-EXCHANGE TRADING BOT")
    print("📊 BTC ARBITRAGE PAPER TRADING")
    print("=" * 65)

    trader = PaperTrader(
        starting_balance=10000.0,
        trade_size=1000.0,
        min_profit_percent=0.10
    )

    print(
        f"\n💰 Startkapital: "
        f"${trader.balance:,.2f}"
    )

    print(
        f"💵 Tradegröße: "
        f"${trader.trade_size:,.2f}"
    )

    print(
        f"🎯 Mindest-Netto: "
        f"{trader.min_profit_percent:.2f}%"
    )

    print(
        f"⏱️ Scan-Intervall: "
        f"{SCAN_INTERVAL} Sekunden"
    )

    print("\n🧪 PAPER TRADING – KEIN ECHTGELD\n")

    try:

        while True:

            print("\n" + "-" * 65)

            print(
                "🔎 Neuer Markt-Scan"
            )

            print(
                datetime_now()
            )

            prices = get_btc_prices()

            opportunity = (
                find_best_opportunity(
                    prices
                )
            )

            if opportunity:

                trader.evaluate_trade(
                    opportunity
                )

            trader.print_statistics()

            print(
                f"\n⏳ Nächster Scan "
                f"in {SCAN_INTERVAL} Sekunden..."
            )

            time.sleep(
                SCAN_INTERVAL
            )

    except KeyboardInterrupt:

        print(
            "\n\n🛑 Paper-Trading beendet."
        )

        trader.print_statistics()


def datetime_now():

    from datetime import datetime

    return datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )


if __name__ == "__main__":

    main()
