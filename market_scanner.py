import ccxt


EXCHANGES = {
    "binance": ccxt.binance({
        "enableRateLimit": True,
        "timeout": 10000,
    }),

    "bybit": ccxt.bybit({
        "enableRateLimit": True,
        "timeout": 10000,
    }),

    "kucoin": ccxt.kucoin({
        "enableRateLimit": True,
        "timeout": 10000,
    }),

    "okx": ccxt.okx({
        "enableRateLimit": True,
        "timeout": 10000,
    }),

    "bitget": ccxt.bitget({
        "enableRateLimit": True,
        "timeout": 10000,
    }),

    "kraken": ccxt.kraken({
        "enableRateLimit": True,
        "timeout": 10000,
    }),

    "coinbase": ccxt.coinbase({
        "enableRateLimit": True,
        "timeout": 10000,
    }),

    "bitrue": ccxt.bitrue({
        "enableRateLimit": True,
        "timeout": 10000,
    }),
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


TRADE_SIZE_USDT = 1000.0
ORDERBOOK_LIMIT = 20


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
                    "bid": float(bid),
                    "ask": float(ask),
                }

                print(
                    f"{name.upper():10} "
                    f"BUY: ${ask:,.2f} | "
                    f"SELL: ${bid:,.2f}",
                    flush=True
                )

        except Exception as e:

            print(
                f"⚠️ {name.upper()}: {e}",
                flush=True
            )

    return prices


def get_orderbooks(available_exchanges):

    orderbooks = {}

    print(
        "\n🔎 Lade echte Orderbücher...",
        flush=True
    )

    for name in available_exchanges:

        exchange = EXCHANGES[name]

        try:

            orderbook = exchange.fetch_order_book(
                "BTC/USDT",
                ORDERBOOK_LIMIT
            )

            asks = orderbook.get(
                "asks",
                []
            )

            bids = orderbook.get(
                "bids",
                []
            )

            if asks and bids:

                orderbooks[name] = {
                    "asks": asks,
                    "bids": bids,
                }

                print(
                    f"✅ {name.upper():10} "
                    f"Orderbuch geladen",
                    flush=True
                )

            else:

                print(
                    f"⚠️ {name.upper():10} "
                    f"leeres Orderbuch",
                    flush=True
                )

        except Exception as e:

            print(
                f"⚠️ {name.upper():10} "
                f"Orderbuch nicht verfügbar: {e}",
                flush=True
            )

    return orderbooks


def calculate_average_buy_price(
    asks,
    usdt_amount
):

    remaining_usdt = float(
        usdt_amount
    )

    btc_amount = 0.0
    total_cost = 0.0

    for level in asks:

        if len(level) < 2:
            continue

        try:

            price = float(level[0])
            quantity = float(level[1])

        except (TypeError, ValueError):

            continue

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

    average_price = (
        total_cost / btc_amount
    )

    return {
        "average_price": average_price,
        "btc_amount": btc_amount,
        "total_cost": total_cost,
    }


def calculate_average_sell_price(
    bids,
    btc_amount
):

    remaining_btc = float(
        btc_amount
    )

    total_revenue = 0.0

    for level in bids:

        if len(level) < 2:
            continue

        try:

            price = float(level[0])
            quantity = float(level[1])

        except (TypeError, ValueError):

            continue

        if price <= 0 or quantity <= 0:
            continue

        amount_to_sell = min(
            remaining_btc,
            quantity
        )

        total_revenue += (
            amount_to_sell * price
        )

        remaining_btc -= (
            amount_to_sell
        )

        if remaining_btc <= 0:

            break

    if remaining_btc > 0:
        return None

    average_price = (
        total_revenue / btc_amount
    )

    return {
        "average_price": average_price,
        "total_revenue": total_revenue,
    }


def calculate_net_arbitrage(
    buy_exchange,
    sell_exchange,
    orderbooks
):

    if buy_exchange not in orderbooks:
        return None

    if sell_exchange not in orderbooks:
        return None

    buy_orderbook = orderbooks[
        buy_exchange
    ]

    sell_orderbook = orderbooks[
        sell_exchange
    ]

    buy_result = (
        calculate_average_buy_price(
            buy_orderbook["asks"],
            TRADE_SIZE_USDT
        )
    )

    if buy_result is None:
        return None

    btc_amount = buy_result[
        "btc_amount"
    ]

    sell_result = (
        calculate_average_sell_price(
            sell_orderbook["bids"],
            btc_amount
        )
    )

    if sell_result is None:
        return None

    average_buy_price = buy_result[
        "average_price"
    ]

    average_sell_price = sell_result[
        "average_price"
    ]

    buy_fee = TRADING_FEES.get(
        buy_exchange,
        0.001
    )

    sell_fee = TRADING_FEES.get(
        sell_exchange,
        0.001
    )

    buy_cost = (
        buy_result["total_cost"]
        * (1 + buy_fee)
    )

    sell_revenue = (
        sell_result["total_revenue"]
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
            "\n❌ Nicht genügend Börsen verfügbar.",
            flush=True
        )

        return None

    orderbooks = get_orderbooks(
        prices.keys()
    )

    if len(orderbooks) < 2:

        print(
            "\n❌ Nicht genügend "
            "Orderbücher verfügbar.",
            flush=True
        )

        return None

    print(
        "\n🧠 Analysiere "
        "Orderbuch-Kombinationen...",
        flush=True
    )

    best_result = None

    exchanges = list(
        orderbooks.keys()
    )

    for buy_exchange in exchanges:

        for sell_exchange in exchanges:

            if buy_exchange == sell_exchange:
                continue

            try:

                result = calculate_net_arbitrage(
                    buy_exchange,
                    sell_exchange,
                    orderbooks
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
                    f"{sell_exchange}: {e}",
                    flush=True
                )

    if best_result is None:

        print(
            "\n❌ Keine auswertbare "
            "Arbitrage gefunden.",
            flush=True
        )

        return None

    print(
        "\n"
        + "=" * 65,
        flush=True
    )

    print(
        "🧠 BTC REAL ORDERBOOK ANALYSIS",
        flush=True
    )

    print(
        "=" * 65,
        flush=True
    )

    print(
        f"Kaufen:       "
        f"{best_result['buy_exchange'].upper()}",
        flush=True
    )

    print(
        f"Ø Kaufpreis:  "
        f"${best_result['buy_price']:,.2f}",
        flush=True
    )

    print(
        f"\nVerkaufen:    "
        f"{best_result['sell_exchange'].upper()}",
        flush=True
    )

    print(
        f"Ø Verkauf:    "
        f"${best_result['sell_price']:,.2f}",
        flush=True
    )

    print(
        f"\nBTC-Menge:    "
        f"{best_result['btc_amount']:.8f}",
        flush=True
    )

    print(
        f"Tradegröße:   "
        f"${best_result['trade_size']:,.2f}",
        flush=True
    )

    print(
        f"Kaufgebühr:   "
        f"{best_result['buy_fee'] * 100:.3f}%",
        flush=True
    )

    print(
        f"Verkaufsgebühr:"
        f" {best_result['sell_fee'] * 100:.3f}%",
        flush=True
    )

    print(
        f"\nNETTO-GEWINN: "
        f"${best_result['net_profit']:.4f}",
        flush=True
    )

    print(
        f"NETTO: "
        f"{best_result['net_profit_percent']:.4f}%",
        flush=True
    )

    if (
        best_result["net_profit_percent"]
        > 0
    ):

        print(
            "\n🟢 THEORETISCH PROFITABEL",
            flush=True
        )

    else:

        print(
            "\n🔴 NICHT PROFITABEL",
            flush=True
        )

    print(
        "=" * 65,
        flush=True
    )

    return best_result


if __name__ == "__main__":

    prices = get_btc_prices()

    find_best_opportunity(
        prices
    )
