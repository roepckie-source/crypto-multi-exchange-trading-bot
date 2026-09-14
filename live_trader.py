import os
import time
from datetime import datetime

import ccxt


# ============================================================
# CONFIG
# ============================================================

MIN_PROFIT_THRESHOLD_PCT = 0.30
TRADE_AMOUNT_USDT = 10.0
MIN_CLEANUP_VALUE_USDT = 5.0

# Sicherheitsbegrenzung:
# 20 Zyklen x 15 Sekunden ~= 5 Minuten
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
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[{timestamp}] {message}", flush=True)


# ============================================================
# EXCHANGES
# ============================================================

def create_exchanges():
    exchanges = {}

    # -------------------------
    # OKX
    # -------------------------

    okx_key = os.getenv("OKX_API_KEY")
    okx_sec = os.getenv("OKX_API_SECRET")
    okx_pass = os.getenv("OKX_PASSPHRASE")

    if okx_key and okx_sec and okx_pass:
        exchanges["OKX"] = ccxt.okx({
            "apiKey": okx_key,
            "secret": okx_sec,
            "password": okx_pass,
            "enableRateLimit": True,
        })

    # -------------------------
    # MEXC
    # -------------------------

    mexc_key = os.getenv("MEXC_API_KEY")
    mexc_sec = os.getenv("MEXC_API_SECRET")

    if mexc_key and mexc_sec:
        exchanges["MEXC"] = ccxt.mexc({
            "apiKey": mexc_key,
            "secret": mexc_sec,
            "enableRateLimit": True,
        })

    # -------------------------
    # BITRUE
    # -------------------------

    bit_key = os.getenv("BITRUE_API_KEY")
    bit_sec = os.getenv("BITRUE_API_SECRET")

    if bit_key and bit_sec:
        exchanges["BITRUE"] = ccxt.bitrue({
            "apiKey": bit_key,
            "secret": bit_sec,
            "enableRateLimit": True,
        })

    return exchanges


# ============================================================
# BALANCES / CLEANUP
# ============================================================

def cleanup_altcoins_to_usdt(exchanges):
    stablecoins = {
        "USDT",
        "USDC",
        "USD",
        "EUR",
    }

    for exchange_name, exchange in exchanges.items():

        try:
            balance = exchange.fetch_balance()

            free_balances = balance.get("free", {})

            for currency, data in free_balances.items():

                if currency in stablecoins:
                    continue

                amount = float(data or 0)

                if amount <= 0:
                    continue

                symbol = f"{currency}/USDT"

                try:
                    ticker = exchange.fetch_ticker(symbol)
                except Exception:
                    continue

                last_price = ticker.get("last")

                if not last_price:
                    continue

                value_usdt = amount * float(last_price)

                if value_usdt < MIN_CLEANUP_VALUE_USDT:
                    continue

                log(
                    f"{exchange_name}: cleanup "
                    f"{amount:.8f} {currency} "
                    f"(~{value_usdt:.2f} USDT)"
                )

                try:
                    exchange.create_market_sell_order(
                        symbol,
                        amount
                    )

                    log(
                        f"{exchange_name}: sold "
                        f"{amount:.8f} {currency}"
                    )

                except Exception as e:
                    log(
                        f"{exchange_name}: cleanup sell failed "
                        f"{currency}: {e}"
                    )

        except Exception as e:
            log(
                f"{exchange_name}: cleanup failed: {e}"
            )


# ============================================================
# ORDERBOOK
# ============================================================

def get_best_prices(exchange, symbol):

    try:
        orderbook = exchange.fetch_order_book(
            symbol,
            limit=5
        )

        bids = orderbook.get("bids", [])
        asks = orderbook.get("asks", [])

        if not bids or not asks:
            return None, None

        best_bid = float(bids[0][0])
        best_ask = float(asks[0][0])

        return best_bid, best_ask

    except Exception as e:

        log(
            f"{exchange.id} {symbol}: "
            f"orderbook error: {e}"
        )

        return None, None


# ============================================================
# FIND BEST ARBITRAGE
# ============================================================

def find_best_arbitrage(exchanges, symbol):

    prices = {}

    for exchange_name, exchange in exchanges.items():

        bid, ask = get_best_prices(
            exchange,
            symbol
        )

        if bid is None or ask is None:
            continue

        prices[exchange_name] = {
            "bid": bid,
            "ask": ask,
        }

    if len(prices) < 2:
        return None

    best_opportunity = None

    for buy_exchange, buy_data in prices.items():

        for sell_exchange, sell_data in prices.items():

            if buy_exchange == sell_exchange:
                continue

            buy_price = buy_data["ask"]
            sell_price = sell_data["bid"]

            if buy_price <= 0:
                continue

            spread_pct = (
                (sell_price - buy_price)
                / buy_price
                * 100
            )

            opportunity = {
                "buy_exchange": buy_exchange,
                "sell_exchange": sell_exchange,
                "buy_price": buy_price,
                "sell_price": sell_price,
                "spread_pct": spread_pct,
            }

            if (
                best_opportunity is None
                or spread_pct
                > best_opportunity["spread_pct"]
            ):
                best_opportunity = opportunity

    return best_opportunity


# ============================================================
# EXECUTE ARBITRAGE
# ============================================================

def execute_arbitrage(
    exchanges,
    symbol,
    opportunity
):

    buy_exchange_name = opportunity[
        "buy_exchange"
    ]

    sell_exchange_name = opportunity[
        "sell_exchange"
    ]

    buy_exchange = exchanges[
        buy_exchange_name
    ]

    sell_exchange = exchanges[
        sell_exchange_name
    ]

    buy_price = opportunity[
        "buy_price"
    ]

    sell_price = opportunity[
        "sell_price"
    ]

    spread_pct = opportunity[
        "spread_pct"
    ]

    if spread_pct < MIN_PROFIT_THRESHOLD_PCT:
        return False

    trade_amount_usdt = TRADE_AMOUNT_USDT

    amount = (
        trade_amount_usdt
        / buy_price
    )

    base_currency = symbol.split("/")[0]

    log(
        f"ARBITRAGE FOUND | {symbol} | "
        f"BUY {buy_exchange_name} "
        f"@ {buy_price:.8f} | "
        f"SELL {sell_exchange_name} "
        f"@ {sell_price:.8f} | "
        f"SPREAD {spread_pct:.4f}% | "
        f"AMOUNT {trade_amount_usdt:.2f} USDT"
    )

    # --------------------------------------------------------
    # BUY
    # --------------------------------------------------------

    try:

        log(
            f"Executing BUY on "
            f"{buy_exchange_name}: "
            f"{amount:.8f} {base_currency}"
        )

        buy_order = (
            buy_exchange.create_market_buy_order(
                symbol,
                amount
            )
        )

        log(
            f"BUY completed: "
            f"{buy_order.get('id', 'unknown')}"
        )

    except Exception as e:

        log(
            f"BUY failed: {e}"
        )

        return False

    # --------------------------------------------------------
    # SELL
    # --------------------------------------------------------

    try:

        log(
            f"Executing SELL on "
            f"{sell_exchange_name}: "
            f"{amount:.8f} {base_currency}"
        )

        sell_order = (
            sell_exchange.create_market_sell_order(
                symbol,
                amount
            )
        )

        log(
            f"SELL completed: "
            f"{sell_order.get('id', 'unknown')}"
        )

        return True

    except Exception as e:

        log(
            "SELL failed after "
            f"successful BUY: {e}"
        )

        return False


# ============================================================
# MAIN
# ============================================================

def main():

    log("=" * 60)
    log("LIVE ARBITRAGE BOT")
    log("=" * 60)

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

    # --------------------------------------------------------
    # CREATE EXCHANGES
    # --------------------------------------------------------

    exchanges = create_exchanges()

    if not exchanges:

        raise RuntimeError(
            "No exchanges configured. "
            "Check API secrets."
        )

    log(
        "Configured exchanges: "
        + ", ".join(exchanges.keys())
    )

    # --------------------------------------------------------
    # INITIAL CLEANUP
    # --------------------------------------------------------

    log(
        "Running initial balance cleanup..."
    )

    cleanup_altcoins_to_usdt(
        exchanges
    )

    # --------------------------------------------------------
    # MAIN TRADING LOOP
    # --------------------------------------------------------

    cycle = 0

    try:

        while cycle < MAX_CYCLES:

            cycle += 1

            log("")
            log("=" * 60)
            log(
                f"CYCLE "
                f"{cycle}/{MAX_CYCLES}"
            )
            log("=" * 60)

            for symbol in SYMBOLS:

                try:

                    opportunity = (
                        find_best_arbitrage(
                            exchanges,
                            symbol
                        )
                    )

                    if not opportunity:

                        log(
                            f"{symbol}: "
                            f"No valid arbitrage data"
                        )

                        continue

                    log(
                        f"{symbol}: "
                        f"BUY "
                        f"{opportunity['buy_exchange']} "
                        f"@ "
                        f"{opportunity['buy_price']:.8f} | "
                        f"SELL "
                        f"{opportunity['sell_exchange']} "
                        f"@ "
                        f"{opportunity['sell_price']:.8f} | "
                        f"SPREAD "
                        f"{opportunity['spread_pct']:.4f}%"
                    )

                    # ------------------------------------------------
                    # TRADE ONLY IF THRESHOLD IS REACHED
                    # ------------------------------------------------

                    if (
                        opportunity["spread_pct"]
                        >= MIN_PROFIT_THRESHOLD_PCT
                    ):

                        execute_arbitrage(
                            exchanges,
                            symbol,
                            opportunity
                        )

                except Exception as e:

                    log(
                        f"{symbol}: "
                        f"cycle error: {e}"
                    )

            # --------------------------------------------------------
            # PERIODIC CLEANUP
            # --------------------------------------------------------

            if cycle % 10 == 0:

                log(
                    "Running periodic cleanup..."
                )

                cleanup_altcoins_to_usdt(
                    exchanges
                )

            # --------------------------------------------------------
            # WAIT BEFORE NEXT CYCLE
            # --------------------------------------------------------

            if cycle < MAX_CYCLES:

                time.sleep(
                    SCAN_INTERVAL_SECONDS
                )

    finally:

        # ------------------------------------------------------------
        # FINAL CLEANUP
        # ------------------------------------------------------------

        log("")
        log("=" * 60)
        log("FINAL CLEANUP")
        log("=" * 60)

        cleanup_altcoins_to_usdt(
            exchanges
        )

        log("=" * 60)
        log("LIVE ARBITRAGE BOT FINISHED")
        log("=" * 60)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()