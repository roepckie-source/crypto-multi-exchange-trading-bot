from market_scanner import get_btc_prices, find_best_opportunity
from paper_trader import PaperTrader


def main():

    print("\n🚀 Crypto Multi-Exchange Trading Bot")
    print("📊 BTC Net Arbitrage Scanner")
    print("🤖 PAPER TRADING MODE\n")

    trader = PaperTrader(
        starting_balance=10000.0,
        trade_size=1000.0,
        min_profit_percent=0.10
    )

    prices = get_btc_prices()

    opportunity = find_best_opportunity(prices)

    if opportunity:
        trader.evaluate_trade(opportunity)

    trader.print_statistics()


if __name__ == "__main__":
    main()
