import asyncio
import logging
import csv
import os
from datetime import datetime

import ccxt.pro as ccxtpro


# ============================================================
# KONFIGURATION
# ============================================================

TRADE_SIZE_USDT = 100.0

# Ziel: mindestens 0,10 % echter Nettogewinn
MIN_NET_PROFIT_PCT = 0.10

# Wir verlangen intern etwas mehr als das Ziel,
# damit kleine Marktbewegungen nicht sofort den Gewinn auffressen.
MIN_ENTRY_PROFIT_PCT = 0.12

# Gebühren pro Leg
KUCOIN_TAKER_FEE = 0.001
BITRUE_TAKER_FEE = 0.00098

# Wie viele Orderbook-Level berücksichtigt werden
ORDERBOOK_LIMIT = 10

# Mindest-24h-Volumen
MIN_24H_VOLUME_USDT = 50_000

# Nicht mehr als diese Anzahl Dreiecke überwachen
MAX_TRIANGLES = 20

# Pause zwischen vollständigen Durchläufen
SCAN_DELAY = 0.5

# Maximale Anzahl Paper-Trades pro Minute
MAX_TRADES_PER_MINUTE = 10

LOG_FILE = "arbitrage_v2.log"
CSV_FILE = "arbitrage_v2_results.csv"


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("ArbitrageV2")


# ============================================================
# CSV
# ============================================================

def init_csv():
    if os.path.exists(CSV_FILE):
        return

    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        writer.writerow([
            "timestamp",
            "exchange",
            "base",
            "pair_a",
            "pair_b",
            "pair_c",
            "start_usdt",
            "final_usdt",
            "profit_usdt",
            "profit_pct",
            "avg_buy_price",
            "avg_sell_btc_price",
            "avg_sell_usdt_price",
            "status"
        ])


def log_trade(result):
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        writer.writerow([
            datetime.utcnow().isoformat(),
            result["exchange"],
            result["base"],
            result["pair_a"],
            result["pair_b"],
            result["pair_c"],
            result["start_usdt"],
            result["final_usdt"],
            result["profit_usdt"],
            result["profit_pct"],
            result["avg_buy_price"],
            result["avg_sell_btc_price"],
            result["avg_sell_usdt_price"],
            result["status"]
        ])


# ============================================================
# ORDERBOOK SIMULATION
# ============================================================

def buy_from_asks(asks, usdt_amount):
    """
    Simuliert einen Market-Buy aus dem Ask-Orderbook.

    Rückgabe:
        base_amount
        tatsächliche USDT-Kosten
        durchschnittlicher Preis
    """

    remaining_usdt = usdt_amount
    bought_amount = 0.0
    spent_usdt = 0.0

    for price, quantity in asks:

        if price <= 0 or quantity <= 0:
            continue

        level_value = price * quantity

        if level_value <= remaining_usdt:
            amount = quantity
        else:
            amount = remaining_usdt / price

        cost = amount * price

        bought_amount += amount
        spent_usdt += cost
        remaining_usdt -= cost

        if remaining_usdt <= 1e-12:
            break

    if spent_usdt < usdt_amount * 0.999999:
        return None

    avg_price = spent_usdt / bought_amount

    return bought_amount, spent_usdt, avg_price


def sell_to_bids(bids, amount):
    """
    Simuliert einen Market-Sell über mehrere Bid-Level.
    """

    remaining_amount = amount
    received = 0.0
    sold_amount = 0.0

    for price, quantity in bids:

        if price <= 0 or quantity <= 0:
            continue

        sell_amount = min(remaining_amount, quantity)

        received += sell_amount * price
        sold_amount += sell_amount
        remaining_amount -= sell_amount

        if remaining_amount <= 1e-12:
            break

    if sold_amount < amount * 0.999999:
        return None

    avg_price = received / sold_amount

    return received, avg_price


# ============================================================
# TRIANGLE BERECHNUNG
# ============================================================

def calculate_triangle(
    trade_size,
    ob_a,
    ob_b,
    ob_c,
    fee
):
    """
    USDT -> COIN -> BTC -> USDT
    """

    if not ob_a.get("asks"):
        return None

    if not ob_b.get("bids"):
        return None

    if not ob_c.get("bids"):
        return None

    # --------------------------------------------------------
    # LEG 1
    # USDT -> COIN
    # --------------------------------------------------------

    buy_result = buy_from_asks(
        ob_a["asks"],
        trade_size
    )

    if not buy_result:
        return None

    coin_amount, spent_usdt, avg_buy_price = buy_result

    # Taker Fee
    coin_after_fee = coin_amount * (1 - fee)

    # --------------------------------------------------------
    # LEG 2
    # COIN -> BTC
    # --------------------------------------------------------

    sell_b_result = sell_to_bids(
        ob_b["bids"],
        coin_after_fee
    )

    if not sell_b_result:
        return None

    btc_received, avg_sell_btc_price = sell_b_result

    btc_after_fee = btc_received * (1 - fee)

    # --------------------------------------------------------
    # LEG 3
    # BTC -> USDT
    # --------------------------------------------------------

    sell_c_result = sell_to_bids(
        ob_c["bids"],
        btc_after_fee
    )

    if not sell_c_result:
        return None

    final_usdt, avg_sell_usdt_price = sell_c_result

    final_usdt *= (1 - fee)

    # --------------------------------------------------------
    # RESULT
    # --------------------------------------------------------

    profit_usdt = final_usdt - trade_size

    profit_pct = (
        profit_usdt / trade_size
    ) * 100

    return {
        "start_usdt": trade_size,
        "final_usdt": final_usdt,
        "profit_usdt": profit_usdt,
        "profit_pct": profit_pct,
        "avg_buy_price": avg_buy_price,
        "avg_sell_btc_price": avg_sell_btc_price,
        "avg_sell_usdt_price": avg_sell_usdt_price
    }


# ============================================================
# PAPER ENGINE
# ============================================================

class PaperEngine:

    def __init__(self, initial_balance=1000.0):

        self.initial_balance = initial_balance
        self.balance = initial_balance

        self.total_trades = 0
        self.winning_trades = 0
        self.total_profit = 0.0

        self.trade_timestamps = []

    def can_trade(self):

        now = asyncio.get_running_loop().time()

        # Nur Trades der letzten 60 Sekunden
        self.trade_timestamps = [
            t for t in self.trade_timestamps
            if now - t < 60
        ]

        return len(self.trade_timestamps) < MAX_TRADES_PER_MINUTE

    def execute(self, result, triangle):

        if not self.can_trade():
            return

        if self.balance < TRADE_SIZE_USDT:
            logger.warning(
                "⚠️ Nicht genügend Paper-Kapital."
            )
            return

        profit = result["profit_usdt"]

        self.balance += profit
        self.total_profit += profit
        self.total_trades += 1

        self.trade_timestamps.append(
            asyncio.get_running_loop().time()
        )

        if profit > 0:
            self.winning_trades += 1

        win_rate = (
            self.winning_trades /
            self.total_trades
        ) * 100

        logger.info("")
        logger.info("=" * 70)
        logger.info(
            f"🔥 PAPER TRADE #{self.total_trades}"
        )

        logger.info(
            f"Asset: {triangle['base']}"
        )

        logger.info(
            f"{triangle['pair_a']} → "
            f"{triangle['pair_b']} → "
            f"{triangle['pair_c']}"
        )

        logger.info(
            f"Start: {TRADE_SIZE_USDT:.2f} USDT"
        )

        logger.info(
            f"Ende: {result['final_usdt']:.6f} USDT"
        )

        logger.info(
            f"Gewinn: {profit:+.6f} USDT"
        )

        logger.info(
            f"Netto: {result['profit_pct']:+.4f}%"
        )

        logger.info(
            f"Paper-Balance: {self.balance:.4f} USDT"
        )

        logger.info(
            f"Win-Rate: {win_rate:.1f}%"
        )

        logger.info("=" * 70)

        log_trade({
            **result,
            "exchange": "kucoin",
            "base": triangle["base"],
            "pair_a": triangle["pair_a"],
            "pair_b": triangle["pair_b"],
            "pair_c": triangle["pair_c"],
            "status": "PAPER_EXECUTED"
        })


# ============================================================
# TRIANGLE FINDER
# ============================================================

async def find_triangles(exchange):

    await exchange.load_markets()

    tickers = await exchange.fetch_tickers()

    usdt_pairs = {}
    btc_pairs = {}

    for symbol, ticker in tickers.items():

        market = exchange.markets.get(symbol)

        if not market:
            continue

        if not market.get("active", True):
            continue

        quote_volume = ticker.get(
            "quoteVolume"
        ) or 0

        if quote_volume < MIN_24H_VOLUME_USDT:
            continue

        base = market["base"]
        quote = market["quote"]

        if quote == "USDT":
            usdt_pairs[base] = symbol

        elif quote == "BTC":
            btc_pairs[base] = symbol

    common = set(usdt_pairs) & set(btc_pairs)

    excluded = {
        "BTC",
        "ETH",
        "SOL",
        "XRP",
        "BNB",
        "USDC",
        "ADA",
        "DOGE"
    }

    common -= excluded

    triangles = []

    for base in common:

        triangles.append({
            "base": base,
            "pair_a": usdt_pairs[base],
            "pair_b": btc_pairs[base],
            "pair_c": "BTC/USDT"
        })

    logger.info(
        f"🔎 Gefundene Dreiecke: {len(triangles)}"
    )

    return triangles[:MAX_TRIANGLES]


# ============================================================
# MONITOR
# ============================================================

async def run():

    init_csv()

    exchange = ccxtpro.kucoin({
        "enableRateLimit": True,
        "timeout": 10000
    })

    paper = PaperEngine(
        initial_balance=1000.0
    )

    try:

        triangles = await find_triangles(exchange)

        if not triangles:
            logger.warning(
                "Keine geeigneten Dreiecke gefunden."
            )
            return

        logger.info("")
        logger.info("🚀 ARBITRAGE ENGINE V2")
        logger.info(
            f"💰 Tradegröße: {TRADE_SIZE_USDT:.2f} USDT"
        )
        logger.info(
            f"🎯 Ziel Netto: {MIN_NET_PROFIT_PCT:.2f}%"
        )
        logger.info(
            f"🛡️ Einstiegsschwelle: {MIN_ENTRY_PROFIT_PCT:.2f}%"
        )
        logger.info(
            f"📚 Orderbook-Level: {ORDERBOOK_LIMIT}"
        )
        logger.info("")
        logger.info("🟢 PAPER MODE AKTIV")
        logger.info("")

        cycle = 0

        while True:

            cycle += 1

            logger.info(
                f"🔄 Scan-Zyklus {cycle}"
            )

            for triangle in triangles:

                try:

                    ob_a = await exchange.fetch_order_book(
                        triangle["pair_a"],
                        limit=ORDERBOOK_LIMIT
                    )

                    ob_b = await exchange.fetch_order_book(
                        triangle["pair_b"],
                        limit=ORDERBOOK_LIMIT
                    )

                    ob_c = await exchange.fetch_order_book(
                        triangle["pair_c"],
                        limit=ORDERBOOK_LIMIT
                    )

                    result = calculate_triangle(
                        TRADE_SIZE_USDT,
                        ob_a,
                        ob_b,
                        ob_c,
                        KUCOIN_TAKER_FEE
                    )

                    if not result:
                        continue

                    profit_pct = result["profit_pct"]

                    # Nur interessante Chancen anzeigen
                    if profit_pct >= 0.05:

                        logger.info(
                            f"👀 {triangle['base']} | "
                            f"Netto: {profit_pct:+.4f}%"
                        )

                    # Paper Trade
                    if (
                        profit_pct >=
                        MIN_ENTRY_PROFIT_PCT
                        and profit_pct >=
                        MIN_NET_PROFIT_PCT
                    ):

                        paper.execute(
                            result,
                            triangle
                        )

                except Exception as e:

                    logger.debug(
                        f"⚠️ Fehler {triangle['base']}: {e}"
                    )

            await asyncio.sleep(
                SCAN_DELAY
            )

    except asyncio.CancelledError:

        logger.info(
            "🛑 Engine gestoppt."
        )

    except Exception as e:

        logger.exception(
            f"❌ Kritischer Fehler: {e}"
        )

    finally:

        await exchange.close()

        logger.info(
            "🔌 Exchange-Verbindung geschlossen."
        )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    asyncio.run(run())
