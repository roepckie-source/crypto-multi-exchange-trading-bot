from market_scanner import (
    get_btc_prices,
    find_best_opportunity
)

from paper_trader import PaperTrader


def main():

    print(
        "\n🚀 Crypto Multi-Exchange Trading Bot"
    )

    print(
        "📊 BTC Net Arbitrage Scanner"
    )

    print(
        "🤖 PAPER TRADING MODE\n"
    )

    # Virtuelles Startkapital
    trader = PaperTrader(
        starting_balance=10000.0,

        # Pro Paper Trade werden
        # maximal 1.000 USDT eingesetzt.
        trade_size=1000.0,

        # Mindestprofit nach Gebühren
        # und angenommener Slippage.
        min_profit_percent=0.10
    )

    # Preise aller erreichbaren Börsen abrufen.
    prices = get_btc_prices()

    # Beste Netto-Arbitrage suchen.
    opportunity = find_best_opportunity(
        prices
    )

    # Wenn eine Opportunity gefunden wurde,
    # an den Paper-Trader übergeben.
    if opportunity:

        trader.evaluate_trade(
            opportunity
        )

    # Statistik ausgeben.
    trader.print_statistics()


if __name__ == "__main__":

    main()
