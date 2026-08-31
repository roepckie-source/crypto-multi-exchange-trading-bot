import os
import sys
import time
from datetime import datetime, timedelta

# CCXT-Bibliothek für Börsenzugriff laden
try:
    import ccxt
except ImportError:
    ccxt = None

# ============================================================
# ⚙️ OPTIMIERTE KONFIGURATION (GEBÜHRENGESICHERT & SCHNELLER SCAN)
# ============================================================

# Top 30 Coins für maximale Volatilität & Arbitrage-Chancen
TOP_30_PAIRS = [
    # Major Coins
    "BTC/USDT",
    "ETH/USDT",
    "SOL/USDT",
    "BNB/USDT",
    "XRP/USDT",
    "ADA/USDT",
    "AVAX/USDT",
    "DOGE/USDT",
    "DOT/USDT",
    "LINK/USDT",
    # Mid-Caps & Volatile Altcoins
    "NEAR/USDT",
    "FET/USDT",
    "RNDR/USDT",
    "SUI/USDT",
    "PEPE/USDT",
    "INJ/USDT",
    "TAO/USDT",
    "APT/USDT",
    "MATIC/USDT",
    "ATOM/USDT",
    "LTC/USDT",
    "BCH/USDT",
    "TRX/USDT",
    "SHIB/USDT",
    "ICP/USDT",
    "FIL/USDT",
    "ETC/USDT",
    "XMR/USDT",
    "TIA/USDT",
    "SEI/USDT",
]

# Exakte Gebührenkalkulation für ECHTEN Reingewinn:
TAKER_FEE_BUY_PCT = 0.10  # Standard Taker-Fee Kauf (~0.10%)
TAKER_FEE_SELL_PCT = 0.10  # Standard Taker-Fee Verkauf (~0.10%)
SLIPPAGE_BUFFER_PCT = 0.05  # Puffer für Preisabweichungen im Orderbuch
NET_PROFIT_GOAL_PCT = 0.05  # Angestrebter Mindest-Reingewinn

# Mindest-Spread = 0.30%
MIN_PROFIT_THRESHOLD_PCT = (
    TAKER_FEE_BUY_PCT
    + TAKER_FEE_SELL_PCT
    + SLIPPAGE_BUFFER_PCT
    + NET_PROFIT_GOAL_PCT
)

# Handelsvolumen pro Trade (in USDT)
TRADE_AMOUNT_USDT = 10.0

# ============================================================
# 🏦 BÖRSEN-INITIALISIERUNG (OKX, MEXC, BITRUE)
# ============================================================


def init_exchanges():
    """Initialisiert die Börsenverbindungen mit deinen GitHub Secrets."""
    exchanges = {}

    if not ccxt:
        print("⚠️ CCXT ist nicht installiert! Skript läuft im Demomodus.")
        return exchanges

    # 1. OKX Initialisierung
    okx_key = os.getenv("OKX_API_KEY")
    okx_secret = os.getenv("OKX_API_SECRET")
    okx_passphrase = os.getenv("OKX_PASSPHRASE")

    if okx_key and okx_secret and okx_passphrase:
        try:
            exchanges["okx"] = ccxt.okx(
                {
                    "apiKey": okx_key,
                    "secret": okx_secret,
                    "password": okx_passphrase,
                    "enableRateLimit": True,
                }
            )
        except Exception as e:
            print(f"⚠️ OKX konnte nicht initialisiert werden: {e}")

    # 2. MEXC Initialisierung
    mexc_key = os.getenv("MEXC_API_KEY")
    mexc_secret = os.getenv("MEXC_API_SECRET")
    if mexc_key and mexc_secret:
        try:
            exchanges["mexc"] = ccxt.mexc(
                {"apiKey": mexc_key, "secret": mexc_secret, "enableRateLimit": True}
            )
        except Exception as e:
            print(f"⚠️ MEXC konnte nicht initialisiert werden: {e}")

    # 3. BITRUE Initialisierung
    bitrue_key = os.getenv("BITRUE_API_KEY")
    bitrue_secret = os.getenv("BITRUE_API_SECRET")
    if bitrue_key and bitrue_secret:
        try:
            exchanges["bitrue"] = ccxt.bitrue(
                {
                    "apiKey": bitrue_key,
                    "secret": bitrue_secret,
                    "enableRateLimit": True,
                }
            )
        except Exception as e:
            print(f"⚠️ BITRUE konnte nicht initialisiert werden: {e}")

    return exchanges


# ============================================================
# ⚡ TRADE-AUSFÜHRUNG (KAUF & VERKAUF PARALLEL)
# ============================================================


def execute_arbitrage(
    buy_exchange, sell_exchange, pair, buy_price, sell_price
):
    """Führt eine Arbitrage-Order auf beiden Börsen aus."""
    try:
        # Erforderliche Menge berechnen
        amount = TRADE_AMOUNT_USDT / buy_price

        print(
            f"\n🚀 STARTE TRADE-AUSFÜHRUNG: {pair} | Volumen: ${TRADE_AMOUNT_USDT} USDT ({amount:.6f} Coins)"
        )

        # 1. Market Buy Order platzieren
        buy_order = buy_exchange.create_market_buy_order(pair, amount)
        buy_id = buy_order.get("id", "N/A")

        # 2. Market Sell Order platzieren
        sell_order = sell_exchange.create_market_sell_order(pair, amount)
        sell_id = sell_order.get("id", "N/A")

        est_profit = (
            TRADE_AMOUNT_USDT * (sell_price - buy_price) / buy_price
        ) - (TRADE_AMOUNT_USDT * 0.002)

        print(f"✅ TRADE ERFOLGREICH AUSGEFÜHRT!")
        print(f"   🟢 Kauf-Order ({buy_exchange.id.upper()}): ID {buy_id}")
        print(f"   🔴 Verkauf-Order ({sell_exchange.id.upper()}): ID {sell_id}")
        print(f"   💰 Geschätzter Netto-Gewinn: +${est_profit:.4f} USD")

        return True, est_profit
    except Exception as e:
        print(f"❌ FEHLER bei der Order-Ausführung auf {pair}: {e}")
        return False, 0.0


# ============================================================
# 🔍 ARBITRAGE SCAN-LOGIK
# ============================================================


def scan_top30_arbitrage(exchanges):
    """Scannt alle Top-30-Paare über die aktiven Börsen und führt Trades aus."""
    stats = {
        "opportunities": 0,
        "success": 0,
        "failed": 0,
        "profit_usd": 0.0,
        "pairs": [],
    }

    print(
        f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🔍 Scanne Top-30-Coins über {len(exchanges)} Börsen..."
    )

    if not exchanges:
        print(
            "⚠️ Keine aktiven API-Börsenverbindungen geladen. Bitte prüfe deine GitHub Secrets."
        )
        return stats

    for pair in TOP_30_PAIRS:
        prices = {}

        # Preise von allen verbundenen Börsen abfragen
        for name, exchange in exchanges.items():
            try:
                ticker = exchange.fetch_ticker(pair)
                if (
                    ticker
                    and "ask" in ticker
                    and "bid" in ticker
                    and ticker["ask"]
                    and ticker["bid"]
                ):
                    prices[name] = {
                        "ask": float(ticker["ask"]),
                        "bid": float(ticker["bid"]),
                    }
                time.sleep(0.05)  # Kurze Pause für API Rate-Limits
            except Exception:
                continue

        # Vergleichen, wenn mindestens 2 Börsen Daten geliefert haben
        if len(prices) >= 2:
            lowest_ask_exchange_name = min(
                prices, key=lambda x: prices[x]["ask"]
            )
            highest_bid_exchange_name = max(
                prices, key=lambda x: prices[x]["bid"]
            )

            buy_price = prices[lowest_ask_exchange_name]["ask"]
            sell_price = prices[highest_bid_exchange_name]["bid"]

            if buy_price > 0 and sell_price > 0:
                gross_spread_pct = ((sell_price - buy_price) / buy_price) * 100
                net_profit_pct = gross_spread_pct - (
                    TAKER_FEE_BUY_PCT + TAKER_FEE_SELL_PCT
                )

                # Bei ausreichendem Spread Trigger auslösen:
                if gross_spread_pct >= MIN_PROFIT_THRESHOLD_PCT:
                    stats["opportunities"] += 1
                    stats["pairs"].append(pair)

                    # Preise präzise formatieren (wichtig bei Memecoins wie PEPE)
                    price_fmt = ".8f" if buy_price < 0.001 else ".4f"

                    print(f"\n⚡ RENTABLE CHANCE GEFUNDEN! Pair: {pair}")
                    print(
                        f"   🟢 Kaufen auf {lowest_ask_exchange_name.upper()}: ${buy_price:{price_fmt}}"
                    )
                    print(
                        f"   🔴 Verkaufen auf {highest_bid_exchange_name.upper()}: ${sell_price:{price_fmt}}"
                    )
                    print(
                        f"   📈 Brutto-Spread: +{gross_spread_pct:.2f}% | Netto-Gewinn: +{net_profit_pct:.2f}%"
                    )

                    # Realen Trade starten
                    buy_ex = exchanges[lowest_ask_exchange_name]
                    sell_ex = exchanges[highest_bid_exchange_name]

                    success, profit = execute_arbitrage(
                        buy_ex, sell_ex, pair, buy_price, sell_price
                    )
                    if success:
                        stats["success"] += 1
                        stats["profit_usd"] += profit
                    else:
                        stats["failed"] += 1

    if stats["opportunities"] == 0:
        print(
            f"ℹ️ Scan abgeschlossen: Keine Preisunterschiede > {MIN_PROFIT_THRESHOLD_PCT:.2f}%."
        )

    return stats


# ============================================================
# 🔄 HAUPTSCHLEIFE MIT SCHNELLEN SCANS (60 SEKUNDEN)
# ============================================================


def run_24h_cycle():
    """Läuft im Dauerbetrieb und scannt alle 60 Sekunden."""
    start_time = datetime.now()
    end_time = start_time + timedelta(hours=24)

    exchanges = init_exchanges()

    daily_summary = {
        "total_runs": 0,
        "total_opportunities": 0,
        "total_success": 0,
        "total_failed": 0,
        "total_profit_usd": 0.0,
        "traded_pairs": set(),
    }

    print("\n" + "=" * 60)
    print("🚀 STARTE SCHNELLEN TRADING-ZYKLUS (TOP 30 ARBITRAGE)")
    print(f"⏱️ Startzeit: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"⏱️ Scan-Intervall: 60 Sekunden")
    print("=" * 60)

    while datetime.now() < end_time:
        daily_summary["total_runs"] += 1
        print(f"\n--- Durchlauf #{daily_summary['total_runs']} ---")

        run_stats = scan_top30_arbitrage(exchanges)

        daily_summary["total_opportunities"] += run_stats.get(
            "opportunities", 0
        )
        daily_summary["total_success"] += run_stats.get("success", 0)
        daily_summary["total_failed"] += run_stats.get("failed", 0)
        daily_summary["total_profit_usd"] += run_stats.get("profit_usd", 0.0)

        for pair in run_stats.get("pairs", []):
            daily_summary["traded_pairs"].add(pair)

        remaining_seconds = (end_time - datetime.now()).total_seconds()
        if remaining_seconds <= 0:
            break

        # KÜRZERES INTERVALL: 60 Sekunden statt 600 Sekunden
        sleep_time = min(60, remaining_seconds)
        print(
            f"⏳ Nächster Top-30-Scan in {int(sleep_time)} Sekunden..."
        )
        time.sleep(sleep_time)

    # 📊 Tagesbericht
    print("\n" + "=" * 60)
    print("📊 LIVE-HANDEL TAGESBERICHT")
    print("=" * 60)
    print(f"🔄 Absolvierte Runs:     {daily_summary['total_runs']}")
    print(f"🔍 Gefundene Chancen:    {daily_summary['total_opportunities']}")
    print(f"✅ Erfolgreiche Trades:  {daily_summary['total_success']}")
    print(
        f"💵 Gesamtgewinn (USD):   +${daily_summary['total_profit_usd']:.4f} USD"
    )
    print("=" * 60 + "\n")


if __name__ == "__main__":
    while True:
        try:
            run_24h_cycle()
        except KeyboardInterrupt:
            print("\n🛑 Bot manuell gestoppt.")
            sys.exit()
        except Exception as e:
            print(f"💥 Fehler im Hauptloop: {e}")
            time.sleep(30)
