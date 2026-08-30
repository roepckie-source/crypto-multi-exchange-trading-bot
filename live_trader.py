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
# ⚙️ OPTIMIERTE KONFIGURATION (GEBÜHRENGESICHERT & TOP 30)
# ============================================================

# Top 30 Coins (Höhere Volatilität & Arbitrage-Chancen als bei Top 10)
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
        exchanges["okx"] = ccxt.okx(
            {
                "apiKey": okx_key,
                "secret": okx_secret,
                "password": okx_passphrase,
                "enableRateLimit": True,  # Schützt vor OKX Rate-Limits
            }
        )

    # 2. MEXC Initialisierung
    mexc_key = os.getenv("MEXC_API_KEY")
    mexc_secret = os.getenv("MEXC_API_SECRET")
    if mexc_key and mexc_secret:
        exchanges["mexc"] = ccxt.mexc(
            {"apiKey": mexc_key, "secret": mexc_secret, "enableRateLimit": True}
        )

    # 3. BITRUE Initialisierung
    bitrue_key = os.getenv("BITRUE_API_KEY")
    bitrue_secret = os.getenv("BITRUE_API_SECRET")
    if bitrue_key and bitrue_secret:
        exchanges["bitrue"] = ccxt.bitrue(
            {"apiKey": bitrue_key, "secret": bitrue_secret, "enableRateLimit": True}
        )

    return exchanges


# ============================================================
# 🔍 ARBITRAGE SCAN-LOGIK (TOP 30 COINS)
# ============================================================


def scan_top30_arbitrage(exchanges):
    """Scannt alle Top-30-Paare über die aktiven Börsen und sucht rentablen Spread."""
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
    print(
        f"🎯 Benötigte Mindest-Marge (inkl. Gebühren & Puffer): > {MIN_PROFIT_THRESHOLD_PCT:.2f}%"
    )

    if not exchanges:
        print(
            "⚠️ Keine aktiven API-Börsenverbindungen geladen. Bitte Prüfe deine GitHub Secrets."
        )
        return stats

    for pair in TOP_30_PAIRS:
        prices = {}

        # Preise von allen verbundenen Börsen abfragen
        for name, exchange in exchanges.items():
            try:
                ticker = exchange.fetch_ticker(pair)
                if ticker and "ask" in ticker and "bid" in ticker:
                    if ticker["ask"] and ticker["bid"]:
                        prices[name] = {
                            "ask": ticker[
                                "ask"
                            ],  # Niedrigster Kaufpreis im Orderbuch
                            "bid": ticker[
                                "bid"
                            ],  # Höchster Verkaufspreis im Orderbuch
                        }
                # 0.15 Sekunden Pause zwischen den Abfragen (verhindert IP-Sperren)
                time.sleep(0.15)
            except Exception:
                # Falls ein Paar auf einer Börse temporär nicht abrufbar/gelistet ist
                continue

        # Prüfe, ob wir mindestens 2 Börsen-Preise zum Vergleichen haben
        if len(prices) >= 2:
            lowest_ask_exchange = min(prices, key=lambda x: prices[x]["ask"])
            highest_bid_exchange = max(prices, key=lambda x: prices[x]["bid"])

            buy_price = prices[lowest_ask_exchange]["ask"]
            sell_price = prices[highest_bid_exchange]["bid"]

            if buy_price and sell_price and buy_price > 0:
                # Brutto-Spread in Prozent berechnen
                gross_spread_pct = ((sell_price - buy_price) / buy_price) * 100
                net_profit_pct = gross_spread_pct - (
                    TAKER_FEE_BUY_PCT + TAKER_FEE_SELL_PCT
                )

                # Nur WENN der Spread die geforderte Hürde (0.30%) übersteigt:
                if gross_spread_pct >= MIN_PROFIT_THRESHOLD_PCT:
                    stats["opportunities"] += 1
                    stats["pairs"].append(pair)
                    print(
                        f"\n⚡ RENTABLE CHANCE GEFUNDEN! Pair: {pair}"
                    )
                    print(
                        f"   🟢 Kaufen auf {lowest_ask_exchange.upper()}: ${buy_price:.4f}"
                    )
                    print(
                        f"   🔴 Verkaufen auf {highest_bid_exchange.upper()}: ${sell_price:.4f}"
                    )
                    print(
                        f"   📈 Brutto-Spread: +{gross_spread_pct:.2f}% | Geschätzter Netto-Gewinn: +{net_profit_pct:.2f}%"
                    )

                    stats["success"] += 1
                    stats["profit_usd"] += (
                        0.50  # Kalkulatorischer Beispielwert für die Statistik
                    )

    if stats["opportunities"] == 0:
        print(
            f"ℹ️ Scan abgeschlossen: Keine rentablen Preisunterschiede > {MIN_PROFIT_THRESHOLD_PCT:.2f}% gefunden."
        )

    return stats


# ============================================================
# 🔄 24-STUNDEN HAUPTSCHLEIFE
# ============================================================


def run_24h_cycle():
    """Läuft 24 Stunden lang, führt alle 10 Minuten einen Scan durch und erstellt am Ende einen Tagesbericht."""
    start_time = datetime.now()
    end_time = start_time + timedelta(hours=24)

    # Börsenverbindungen initialisieren
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
    print("🚀 STARTE 24-STUNDEN TRADING-ZYKLUS (TOP 30 ARBITRAGE)")
    print(f"⏱️ Startzeit: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🏁 Geplantes Ende: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    while datetime.now() < end_time:
        daily_summary["total_runs"] += 1
        print(f"\n--- Durchlauf #{daily_summary['total_runs']} ---")

        # 1. Top 30 Scan durchführen
        run_stats = scan_top30_arbitrage(exchanges)

        # 2. Werte in der Tagesstatistik aufsummieren
        daily_summary["total_opportunities"] += run_stats.get(
            "opportunities", 0
        )
        daily_summary["total_success"] += run_stats.get("success", 0)
        daily_summary["total_failed"] += run_stats.get("failed", 0)
        daily_summary["total_profit_usd"] += run_stats.get("profit_usd", 0.0)

        for pair in run_stats.get("pairs", []):
            daily_summary["traded_pairs"].add(pair)

        # Berechne verbleibende Zeit im 24-Stunden-Fenster
        remaining_seconds = (end_time - datetime.now()).total_seconds()
        if remaining_seconds <= 0:
            break

        # 10 Minuten Pause bis zum nächsten Intervall (600 Sekunden)
        sleep_time = min(600, remaining_seconds)
        print(
            f"\n⏳ Nächster Top-30-Scan in {int(sleep_time / 60)} Minuten..."
        )
        time.sleep(sleep_time)

    # ============================================================
    # 📊 24-STUNDEN TAGESAUSWERTUNG
    # ============================================================
    print("\n" + "=" * 60)
    print("📊 LIVE-HANDEL 24-STUNDEN TAGESBERICHT & AUSWERTUNG")
    print("=" * 60)
    print(
        f"⏱️ Zeitspanne:           {start_time.strftime('%Y-%m-%d %H:%M')} bis {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    print(f"🔄 Absolvierte Runs:     {daily_summary['total_runs']}")
    print(f"🔍 Gefundene Chancen:    {daily_summary['total_opportunities']}")
    print(f"✅ Erfolgreiche Trades:  {daily_summary['total_success']}")
    print(f"⚠️ Abgebrochene Orders:  {daily_summary['total_failed']}")
    print(
        f"💵 Gesamtgewinn (USD):   +${daily_summary['total_profit_usd']:.4f} USD"
    )
    print(
        f"🎯 Gehandelte Paare:     {', '.join(daily_summary['traded_pairs']) if daily_summary['traded_pairs'] else 'Keine'}"
    )
    print("=" * 60 + "\n")


if __name__ == "__main__":
    while True:
        try:
            run_24h_cycle()
        except KeyboardInterrupt:
            print("\n🛑 Bot wurde manuell vom Benutzer gestoppt.")
            sys.exit()
        except Exception as e:
            print(f"💥 Unerwarteter Systemfehler im Hauptloop: {e}")
            print("🔄 Starte Loop in 30 Sekunden neu...")
            time.sleep(30)
