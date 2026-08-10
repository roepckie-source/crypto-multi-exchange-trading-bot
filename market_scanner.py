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


# Virtuelle Tradegröße
TRADE_SIZE_USDT = 1000.0


def get_btc_prices():

    prices = {}

    for name, exchange in EXCHANGES.items():

        try:

            ticker = exchange.fetch_ticker(
                "BTC/USDT"
            )

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

            print(
                f"⚠️ {name.upper()}: {e}"
            )

    return prices


def get_orderbook(exchange, limit=20):

    try:

        return exchange.fetch_order_book(
            "BTC/USDT",
            limit
        )

    except Exception as e:

        print(
            f"⚠️ Orderbuch-Fehler: {e}"
        )

        return None


def calculate_average_buy_price(
    asks,
    usdt_amount
):

    remaining_usdt = usdt_amount
    btc_amount = 0.0
    total_cost = 0.0

    for price, quantity in asks:

        if price <= 0 or quantity <= 0:
            continue

        available_usdt = (
            price * quantity
        )

        amount_to_use = min(
            remaining_usdt,
            available_usdt
        )

        btc_bought = (
            amount_to_use / price
        )

        btc_amount += btc_bought
        total_cost += amount_to_use

        remaining_usdt -= amount_to_use

        if remaining_usdt <= 0:
            break

    if btc_amount <= 0:
        return None

    if remaining_usdt > 0:
        return None

    return total_cost / btc_amount


def calculate_average_sell_price(
    bids,
    btc_amount
):

    remaining_btc = btc_amount
    total_revenue = 0.0

    for price, quantity in bids:

        if price <= 0 or quantity <= 0:
            continue

        amount_to_sell = min(
            remaining_btc,
            quantity
        )

        total_revenue += (
            amount_to_sell * price
        )

        remaining_btc -= amount_to_sell

        if remaining_btc <= 0:
            break

    if remaining_btc > 0:
        return None

    return (
        total_revenue
        / btc_amount
    )


def calculate_net_arbitrage(
    buy_exchange,
    sell_exchange
):

    buy_market = EXCHANGES[
        buy_exchange
    ]

    sell_market = EXCHANGES[
        sell_exchange
    ]

    buy_orderbook = get_orderbook(
        buy_market
    )

    sell_orderbook = get_orderbook(
        sell_market
    )

    if not buy_orderbook:
        return None

    if not sell_orderbook:
        return None

    asks = buy_orderbook.get(
        "asks",
        []
    )

    bids = sell_orderbook.get(
        "bids",
        []
    )

    if not asks or not bids:
        return None

    average_buy_price = (
        calculate_average_buy_price(
            asks,
            TRADE_SIZE_USDT
        )
    )

    if average_buy_price is None:
        return None

    btc_amount = (
        TRADE_SIZE_USDT
        / average_buy_price
    )

    average_sell_price = (
        calculate_average_sell_price(
            bids,
            btc_amount
        )
    )

    if average_sell_price is None:
        return None

    buy_fee = TRADING_FEES.get(
        buy_exchange,
        0.001
    )

    sell_fee = TRADING_FEES.get(
        sell_exchange,
        0.001
    )

    buy_cost = (
        TRADE_SIZE_USDT
        * (1 + buy_fee)
    )

    sell_revenue = (
        btc_amount
        * average_sell_price
        * (1 - sell_fee)
    )

    net_profit = (
        sell_revenue
        - buy_cost
    )

    net_profit_percent = (
        net_profit
        / buy_cost
    ) * 100

    return {

        "buy_exchange":
            buy_exchange,

        "sell_exchange":
            sell_exchange,

        "buy_price":
            average_buy_price,

        "sell_price":
            average_sell_price,

        "buy_fee":
            buy_fee,

        "sell_fee":
            sell_fee,

        "trade_size":
            TRADE_SIZE_USDT,

        "btc_amount":
            btc_amount,

        "net_profit":
            net_profit,

        "net_profit_percent":
            net_profit_percent,
    }


def find_best_opportunity(prices):

    if len(prices) < 2:

        print(
            "\n❌ Nicht genügend Börsen verfügbar."
        )

        return None

    best_result = None

    exchanges = list(
        prices.keys()
    )

    print(
        "\n🔎 Analysiere Orderbücher..."
    )

    for buy_exchange in exchanges:

        for sell_exchange in exchanges:

            if buy_exchange == sell_exchange:
                continue

            try:

                result = calculate_net_arbitrage(
                    buy_exchange,
                    sell_exchange
                )

                if result is None:
                    continue

                if (
                    best_result is None
                    or result[
                        "net_profit_percent"
                    ]
                    > best_result[
                        "net_profit_percent"
                    ]
                ):

                    best_result = result

            except Exception as e:

                print(
                    f"⚠️ "
                    f"{buy_exchange} → "
                    f"{sell_exchange}: "
                    f"{e}"
                )

    if best_result is None:

        print(
            "\n❌ Keine auswertbare "
            "Arbitrage gefunden."
        )

        return None

    print(
        "\n"
        + "=" * 65
    )

    print(
        "🧠 BTC REAL ORDERBOOK ANALYSIS"
    )

    print(
        "=" * 65
    )

    print(
        f"Kaufen:       "
        f"{best_result['buy_exchange'].upper()}"
    )

    print(
        f"Ø Kaufpreis:  "
        f"${best_result['buy_price']:,.2f}"
    )

    print(
        f"\nVerkaufen:    "
        f"{best_result['sell_exchange'].upper()}"
    )

    print(
        f"Ø Verkauf:    "
        f"${best_result['sell_price']:,.2f}"
    )

    print(
        f"\nBTC-Menge:    "
        f"{best_result['btc_amount']:.8f}"
    )

    print(
        f"Tradegröße:   "
        f"${best_result['trade_size']:,.2f}"
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
        f"\nNETTO-GEWINN: "
        f"${best_result['net_profit']:.4f}"
    )

    print(
        f"NETTO: "
        f"{best_result['net_profit_percent']:.4f}%"
    )

    if (
        best_result["net_profit_percent"]
        > 0
    ):

        print(
            "\n🟢 THEORETISCH PROFITABEL"
        )

    else:

        print(
            "\n🔴 NICHT PROFITABEL"
        )

    print(
        "=" * 65
    )

    return best_result


if __name__ == "__main__":

    prices = get_btc_prices()

    find_best_opportunity(
        prices
    )
