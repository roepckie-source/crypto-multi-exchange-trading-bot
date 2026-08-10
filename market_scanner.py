import ccxt


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


# Geschätzte Spot-Handelsgebühren.
# Diese Werte sind konservative Startwerte und werden später
# durch die tatsächlichen Gebühren der jeweiligen Accounts ersetzt.
TRADING_FEES = {
    "binance": 0.0010,
    "bybit": 0.0010,
    "kucoin": 0.0010,
    "okx": 0.0010,
    "bitget": 0.0010,
    "kraken": 0.0026,
    "coinbase": 0.0040,
    "bitrue": 0.0020,
}


# Sicherheitsannahme für die anfängliche Slippage-Berechnung.
ESTIMATED_SLIPPAGE = 0.0005


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


def calculate_net_arbitrage(
    buy_exchange,
    buy_price,
    sell_exchange,
    sell_price
):
    buy_fee = TRADING_FEES.get(buy_exchange, 0.001)
    sell_fee = TRADING_FEES.get(sell_exchange, 0.001)

    # Kosten beim Kauf
    effective_buy_price = (
        buy_price
        * (1 + buy_fee + ESTIMATED_SLIPPAGE)
    )

    # Erlös beim Verkauf
    effective_sell_price = (
        sell_price
        * (1 - sell_fee - ESTIMATED_SLIPPAGE)
    )

    net_profit = effective_sell_price - effective_buy_price

    net_profit_percent = (
        net_profit / effective_buy_price
    ) * 100

    return {
        "buy_fee": buy_fee,
        "sell_fee": sell_fee,
        "effective_buy_price": effective_buy_price,
        "effective_sell_price": effective_sell_price,
        "net_profit": net_profit,
        "net_profit_percent": net_profit_percent,
    }


def find_best_opportunity(prices):

    if len(prices) < 2:
        print("\n❌ Nicht genügend Börsen verfügbar.")
        return

    best_result = None

    exchanges = list(prices.keys())

    for buy_exchange in exchanges:

        for sell_exchange in exchanges:

            if buy_exchange == sell_exchange:
                continue

            buy_price = prices[buy_exchange]["ask"]
            sell_price = prices[sell_exchange]["bid"]

            gross_spread = sell_price - buy_price

            if gross_spread <= 0:
                continue

            gross_spread_percent = (
                gross_spread / buy_price
            ) * 100

            result = calculate_net_arbitrage(
                buy_exchange,
                buy_price,
                sell_exchange,
                sell_price
            )

            result["buy_exchange"] = buy_exchange
            result["sell_exchange"] = sell_exchange
            result["buy_price"] = buy_price
            result["sell_price"] = sell_price
            result["gross_spread"] = gross_spread
            result["gross_spread_percent"] = gross_spread_percent

            if (
                best_result is None
                or result["net_profit_percent"]
                > best_result["net_profit_percent"]
            ):
                best_result = result

    if best_result is None:
        print("\n❌ Keine positive Brutto-Arbitrage gefunden.")
        return

    print("\n" + "=" * 65)
    print("🧠 BTC NET ARBITRAGE ANALYSIS")
    print("=" * 65)

    return best_result

    print(
        f"Kaufen:       "
        f"{best_result['buy_exchange'].upper()}"
    )

    print(
        f"Kaufpreis:    "
        f"${best_result['buy_price']:,.2f}"
    )

    print(
        f"\nVerkaufen:    "
        f"{best_result['sell_exchange'].upper()}"
    )

    print(
        f"Verkaufspreis:"
        f" ${best_result['sell_price']:,.2f}"
    )

    print(
        f"\nBrutto-Spread: "
        f"{best_result['gross_spread_percent']:.4f}%"
    )

    print(
        f"Kaufgebühr:   "
        f"{best_result['buy_fee'] * 100:.3f}%"
    )

    print(
        f"Verkaufsgebühr:"
        f" {best_result['sell_fee'] * 100:.3f}%"
    )

    print(
        f"Slippage:     "
        f"{ESTIMATED_SLIPPAGE * 100:.3f}% je Seite"
    )

    print(
        f"\nEffektiver Kauf:"
        f" ${best_result['effective_buy_price']:,.2f}"
    )

    print(
        f"Effektiver Verkauf:"
        f" ${best_result['effective_sell_price']:,.2f}"
    )

    print(
        f"\nNETTO-GEWINN: "
        f"${best_result['net_profit']:.2f}"
    )

    print(
        f"NETTO: "
        f"{best_result['net_profit_percent']:.4f}%"
    )

    if best_result["net_profit_percent"] > 0:
        print("\n🟢 THEORETISCH PROFITABEL")
    else:
        print("\n🔴 NICHT PROFITABEL")

    print("=" * 65)


def main():

    print("\n🚀 Crypto Multi-Exchange Trading Bot")
    print("📊 BTC Net Arbitrage Scanner")
    print("🧪 MODE: PAPER TRADING\n")

    prices = get_btc_prices()

    find_best_opportunity(prices)


if __name__ == "__main__":
    main()
