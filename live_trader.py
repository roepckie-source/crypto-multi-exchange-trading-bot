import os
import time
from datetime import datetime, UTC

import ccxt


# ============================================================
# CONFIG
# ============================================================

MIN_PROFIT_THRESHOLD_PCT = 0.30
TRADE_AMOUNT_USDT = 10.0
MIN_CLEANUP_VALUE_USDT = 5.0

MAX_CYCLES = 20
SCAN_INTERVAL_SECONDS = 15

SYMBOLS = [
    "BTC/USDT",
    "ETH/USDT",
    "SOL/USDT",
    "XRP/USDT",
    "ADA/USDT",
    "DOGE/USDT",
    "LTC/USDT",
]


# ============================================================
# LOGGING
# ============================================================

def log(message):
    print(
        f"[{datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')}] "
        f"{message}",
        flush=True,
    )


# ============================================================
# CREATE EXCHANGES
# ============================================================

def create_exchanges():

    exchanges = {}

    # --------------------------------------------------------
    # OKX
    # --------------------------------------------------------

    okx_key = os.getenv("OKX_API_KEY")
    okx_sec = os.getenv("OKX_API_SECRET")
    okx_pass = os.getenv("OKX_PASSPHRASE")

    if okx_key and okx_sec and okx_pass:

        exchanges["OKX"] = ccxt.okx({
            "apiKey": okx_key,
            "secret": okx_sec,
            "password": okx_pass,
            "enableRateLimit": True,

            # EEA endpoint
            "hostname": "eea.okx.com",
        })

    else:
        log("WARNING: OKX credentials missing")

    # --------------------------------------------------------
    # MEXC
    # --------------------------------------------------------

    mexc_key = os.getenv("MEXC_API_KEY")
    mexc_sec = os.getenv("MEXC_API_SECRET")

    if mexc_key and mexc_sec:

        exchanges["MEXC"] = ccxt.mexc({
            "apiKey": mexc_key,
            "secret": mexc_sec,
            "enableRateLimit": True,
        })

    else:
        log("WARNING: MEXC credentials missing")

    # --------------------------------------------------------
    # BITRUE
    # --------------------------------------------------------

    bitrue_key = os.getenv("BITRUE_API_KEY")
    bitrue_sec = os.getenv("BITRUE_API_SECRET")

    if bitrue_key and bitrue_sec:

        exchanges["BITRUE"] = ccxt.bitrue({
            "apiKey": bitrue_key,
            "secret": bitrue_sec,
            "enableRateLimit": True,
        })

    else:
        log("WARNING: BITRUE credentials missing")

    return exchanges


# ============================================================
# CLEANUP ALTCOINS
# ============================================================

def cleanup_altcoins_to_usdt(exchanges):

    log("Running balance cleanup...")

    stablecoins = {
        "USDT",
        "USDC",
        "USD",
        "DAI",
        "FDUSD",
        "TUSD",
    }

    for name, exchange in exchanges.items():

        try:

            balance = exchange.fetch_balance()

            free_balances = balance.get("free", {})

            for currency, amount in free_balances.items():

                if currency in stablecoins:
                    continue

                if not amount or amount <= 0:
                    continue

                symbol = f"{currency}/USDT"

                try:

                    ticker = exchange.fetch_ticker(symbol)

                    last_price = ticker.get("last")

                    if not last_price:
                        continue

                    value_usdt = amount * last_price

                    if value_usdt < MIN_CLEANUP_VALUE_USDT:
                        continue

                    log(
                        f"{name}: cleaning {amount} {currency} "
                        f"(~{value_usdt:.2f} USDT)"
                    )

                    exchange.create_market_sell_order(
                        symbol,
                        amount,
                    )

                    log(
                        f"{name}: sold {amount} {currency} "
                        f"into USDT"
                    )

                except Exception as e:

                    log(
                        f"{name}: cleanup failed for "
                        f"{currency}: {e}"
                    )

        except Exception as e:

            log(
                f"{name}: balance cleanup failed: {e}"
            )


# ============================================================
# GET BEST PRICES
# ============================================================

def get_best_prices(exchanges, symbol):

    prices = {}

    for name, exchange in exchanges.items():

        try:

            orderbook = exchange.fetch_order_book(
                symbol,
                limit=5,
            )

            bids = orderbook.get("bids", [])
            asks = orderbook.get("asks", [])

            if not bids or not asks:
                continue

            best_bid = bids[0][0]
            best_ask = asks[0][0]

            prices[name] = {
                "bid": best_bid,
                "ask": best_ask,
            }

        except Exception as e:

            log(
                f"{name} {symbol}: "
                f"orderbook failed: {e}"
            )

    return prices


# ============================================================
# FIND BEST ARBITRAGE
# ============================================================

def find_best_arbitrage(prices, symbol):

    best_trade = None

    exchange_names = list(prices.keys())

    for buy_exchange in exchange_names:

        for sell_exchange in exchange_names:

            if buy_exchange == sell_exchange:
                continue

            buy_price = prices[buy_exchange]["ask"]
            sell_price = prices[sell_exchange]["bid"]

            if not buy_price or not sell_price:
                continue

            spread_pct = (
                (sell_price - buy_price)
                / buy_price
                * 100
            )

            if (
                best_trade is None
                or spread_pct > best_trade["spread_pct"]
            ):

                best_trade = {
                    "symbol": symbol,
                    "buy_exchange": buy_exchange,
                    "sell_exchange": sell_exchange,
                    "buy_price": buy_price,
                    "sell_price": sell_price,
                    "spread_pct": spread_pct,
                }

    return best_trade


# ============================================================
# EXECUTE ARBITRAGE
# ============================================================

def execute_arbitrage(trade, exchanges):

    symbol = trade["symbol"]

    buy_exchange_name = trade["buy_exchange"]
    sell_exchange_name = trade["sell_exchange"]

    buy_price = trade["buy_price"]
    sell_price = trade["sell_price"]

    spread_pct = trade["spread_pct"]

    log(
        f"ARBITRAGE FOUND: {symbol} | "
        f"BUY {buy_exchange_name} @ {buy_price:.8f} | "
        f"SELL {sell_exchange_name} @ {sell_price:.8f} | "
        f"SPREAD {spread_pct:.4f}%"
    )

    if spread_pct < MIN_PROFIT_THRESHOLD_PCT:

        log(
            f"Spread {spread_pct:.4f}% below threshold "
            f"{MIN_PROFIT_THRESHOLD_PCT:.2f}%"
        )

        return False

    buy_exchange = exchanges[buy_exchange_name]
    sell_exchange = exchanges[sell_exchange_name]

    amount = TRADE_AMOUNT_USDT / buy_price

    try:

        log(
            f"Executing BUY: "
            f"{amount:.8f} {symbol}"
        )

        buy_order = buy_exchange.create_market_buy_order(
            symbol,
            amount,
        )

        log(
            f"BUY executed on {buy_exchange_name}: "
            f"{buy_order}"
        )

    except Exception as e:

        log(
            f"BUY FAILED on {buy_exchange_name}: {e}"
        )

        return False

    try:

        log(
            f"Executing SELL: "
            f"{amount:.8f} {symbol}"
        )

        sell_order = sell_exchange.create_market_sell_order(
            symbol,
            amount,
        )

        log(
            f"SELL executed on {sell_exchange_name}: "
            f"{sell_order}"
        )

    except Exception as e:

        log(
            f"SELL FAILED on {sell_exchange_name}: {e}"
        )

        return False

    return True


# ============================================================
# MAIN
# ============================================================

def main():

    log("==================================================")
    log("LIVE ARBITRAGE BOT")
    log("==================================================")

    log(
        f"MAX_CYCLES = {MAX_CYCLES}"
    )

    log(
        f"SCAN_INTERVAL_SECONDS = "
        f"{SCAN_INTERVAL_SECONDS}"
    )

    log(
        f"MIN_PROFIT_THRESHOLD_PCT = "
        f"{MIN_PROFIT_THRESHOLD_PCT}%"
    )

    log(
        f"TRADE_AMOUNT_USDT = "
        f"{TRADE_AMOUNT_USDT}"
    )

    exchanges = create_exchanges()

    log(
        "Configured exchanges: "
        + ", ".join(exchanges.keys())
    )

    # --------------------------------------------------------
    # INITIAL CLEANUP
    # --------------------------------------------------------

    log("Running initial balance cleanup...")

    cleanup_altcoins_to_usdt(exchanges)

    # --------------------------------------------------------
    # MAIN LOOP
    # --------------------------------------------------------

    for cycle in range(1, MAX_CYCLES + 1):

        log("")
        log("==================================================")
        log(
            f"CYCLE {cycle}/{MAX_CYCLES}"
        )
        log("==================================================")

        for symbol in SYMBOLS:

            try:

                prices = get_best_prices(
                    exchanges,
                    symbol,
                )

                if len(prices) < 2:

                    log(
                        f"{symbol}: "
                        f"not enough exchange prices"
                    )

                    continue

                trade = find_best_arbitrage(
                    prices,
                    symbol,
                )

                if not trade:
                    continue

                log(
                    f"{symbol}: "
                    f"BUY {trade['buy_exchange']} "
                    f"{trade['buy_price']:.8f} | "
                    f"SELL {trade['sell_exchange']} "
                    f"{trade['sell_price']:.8f} | "
                    f"SPREAD "
                    f"{trade['spread_pct']:.4f}%"
                )

                if (
                    trade["spread_pct"]
                    >= MIN_PROFIT_THRESHOLD_PCT
                ):

                    execute_arbitrage(
                        trade,
                        exchanges,
                    )

            except Exception as e:

                log(
                    f"{symbol}: cycle error: {e}"
                )

        # ----------------------------------------------------
        # PERIODIC CLEANUP
        # ----------------------------------------------------

        if cycle % 10 == 0:

            log(
                "Periodic balance cleanup..."
            )

            cleanup_altcoins_to_usdt(
                exchanges
            )

        # ----------------------------------------------------
        # WAIT
        # ----------------------------------------------------

        if cycle < MAX_CYCLES:

            time.sleep(
                SCAN_INTERVAL_SECONDS
            )

    # --------------------------------------------------------
    # FINAL CLEANUP
    # --------------------------------------------------------

    log("")
    log("==================================================")
    log("FINAL CLEANUP")
    log("==================================================")

    cleanup_altcoins_to_usdt(exchanges)

    log("")
    log("==================================================")
    log("LIVE ARBITRAGE BOT FINISHED")
    log("==================================================")


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()