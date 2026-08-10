import ccxt
import time


EXCHANGES = {
    "binance": ccxt.binance(),
    "bybit": ccxt.bybit(),
    "kucoin": ccxt.kucoin(),
    "okx": ccxt.okx(),
    "bitget": ccxt.bitget(),
    "kraken": ccxt.kraken(),
    "coinbase": ccxt.coinbase(),
    "bitrue": ccxt.bitrue(),
}


def get_btc_prices():
    prices = {}

    for name, exchange in EXCHANGES.items():
        try:
            ticker = exchange.fetch_ticker("BTC/USDT")

            bid = ticker.get("bid")
            ask = ticker.get("ask")

            if bid and ask:
                prices[name] = {
                    "bid": bid,
                    "ask": ask,
                }

                print(
                    f"{name.upper():10} "
                    f"BUY: ${ask:,.2f} | "
                    f"SELL: ${bid:,.2f}"
                )

        except Exception as e:
            print(f"⚠️ {name.upper()}: {e}")

    return prices


def find_best_opportunity(prices):
    if len(prices) < 2:
        print("\n❌ Nicht genügend Börsen verfügbar.")
        return

    best_buy = min(
        prices.items(),
        key=lambda x: x[1]["ask"]
    )

    best_sell = max(
        prices.items(),
        key=lambda x: x[1]["bid"]
    )

    buy_exchange, buy_data = best_buy
    sell_exchange, sell_data = best_sell

    spread = sell_data["bid"] - buy_data["ask"]
    spread_percent = (spread / buy_data["ask"]) * 100

    print("\n" + "=" * 60)
    print("🚀 BESTE BTC-ARBITRAGE-CHANCE")
    print("=" * 60)

    print(f"Kaufen:  {buy_exchange.upper()}")
    print(f"Preis:   ${buy_data['ask']:,.2f}")

    print(f"\nVerkaufen: {sell_exchange.upper()}")
    print(f"Preis:     ${sell_data['bid']:,.2f}")

    print(f"\nSpread: ${spread:,.2f}")
    print(f"Spread %: {spread_percent:.4f}%")

    if spread_percent > 0:
        print("🟢 Positive Preis-Differenz")
    else:
        print("🔴 Keine Arbitrage")

    print("=" * 60)


def main():
    print("\n🚀 Crypto Multi-Exchange Trading Bot")
    print("📊 BTC Market Scanner")
    print("🧪 MODE: PAPER TRADING\n")

    while True:
        prices = get_btc_prices()

        find_best_opportunity(prices)

        print("\n⏳ Nächster Scan in 30 Sekunden...\n")

        time.sleep(30)


if __name__ == "__main__":
    main()
