import itertools
import os
import sys
import time

try:
    import ccxt
except ImportError:
    print("❌ CCXT ist nicht installiert! Bitte 'pip install ccxt' ausführen.")
    sys.exit(1)

# ============================================================
# ⚙️ TRADER KONFIGURATION
# ============================================================

# Mindestmarge in % für Arbitrage-Trades
MIN_PROFIT_THRESHOLD_PCT = 0.30

# Fester Order-Betrag in USDT pro Arbitrage-Trade
TRADE_AMOUNT_USDT = 10.0

# Mindest-Gegenwert in USDT für den Altcoin-Auto-Cleanup (verhindert 'Min Notional'-Fehler)
MIN_CLEANUP_VALUE_USDT = 5.0

# Zu überwachende Handelspaare
SYMBOLS_TO_SCAN = [
    "BTC/USDT",
    "ETH/USDT",
    "SOL/USDT",
    "XRP/USDT",
    "ADA/USDT",
    "DOGE/USDT",
    "LTC/USDT",
]

# ============================================================
# 🏦 BÖRSEN INITIALISIEREN
# ============================================================


def init_exchanges():
    exchanges = {}

    # OKX (EEA-Fix für EU)
    okx_key, okx_sec, okx_pass = (
        os.getenv("OKX_API_KEY"),
        os.getenv("OKX_API_SECRET"),
        os.getenv("OKX_PASSPHRASE"),
    )
    if okx_key and okx_sec and okx_pass:
        try:
            exchanges["okx"] = ccxt.okx(
                {
                    "apiKey": okx_key,
                    "secret": okx_sec,
                    "password": okx_pass,
                    "hostname": "my.okx.com",
                    "enableRateLimit": True,
                }
            )
        except Exception as e:
            print(f"❌ Fehler bei OKX: {e}")

    # MEXC
    mexc_key, mexc_sec = os.getenv("MEXC_API_KEY"), os.getenv("MEXC_API_SECRET")
    if mexc_key and mexc_sec:
        try:
            exchanges["mexc"] = ccxt.mexc(
                {"apiKey": mexc_key, "secret": mexc_sec, "enableRateLimit": True}
            )
        except Exception as e:
            print(f"❌ Fehler bei MEXC: {e}")

    # BITRUE
    bit_key, bit_sec = os.getenv("BITRUE_API_KEY"), os.getenv("BITRUE_API_SECRET")
    if bit_key and bit_sec:
        try:
            exchanges["bitrue"] = ccxt.bitrue(
                {"apiKey": bit_key, "secret": bit_sec, "enableRateLimit": True}
            )
        except Exception as e:
            print(f"❌ Fehler bei BITRUE: {e}")

    return exchanges


# ============================================================
# 🧹 ALTCOIN AUTO-CLEANUP (MARKT-VERKAUF IN USDT)
# ============================================================


def cleanup_altcoins_to_usdt(exchanges):
    """Prüft alle Börsen auf vorhandene Altcoins und tauscht diese direkt per Market-Sell in USDT um."""
    print("\n🧹 Starte Altcoin-Auto-Cleanup auf allen Börsen...")

    for name, ex in exchanges.items():
        ex_name = name.upper()
        try:
            balance = ex.fetch_balance()
            free_balances = balance.get("free", {})

            for coin, amount in free_balances.items():
                if coin in ["USDT", "USD", "USDC"] or amount <= 0:
                    continue

                symbol = f"{coin}/USDT"

                try:
                    ticker = ex.fetch_ticker(symbol)
                    current_price = ticker["last"]
                except Exception:
                    continue

                estimated_value_usdt = amount * current_price

                if estimated_value_usdt < MIN_CLEANUP_VALUE_USDT:
                    print(
                        f"ℹ️ [{ex_name}] {coin}: Wert (${estimated_value_usdt:.2f}) unter Minimum (${MIN_CLEANUP_VALUE_USDT:.2f}). Überspringe."
                    )
                    continue

                print(
                    f"⚡ [{ex_name}] Tausche {amount:.4f} {coin} (~${estimated_value_usdt:.2f} USDT) per Market-Sell in USDT..."
                )

                try:
                    order = ex.create_market_sell_order(symbol, amount)
                    order_id = order.get("id", "N/A")
                    print(
                        f"✅ [{ex_name}] Erfolgreich verkauft! Order-ID: {order_id}"
                    )
                except Exception as e:
                    print(f"❌ [{ex_name}] Fehler beim Verkauf von {coin}: {e}")

        except Exception as e:
            print(f"❌ [{ex_name}] Fehler beim Abrufen des Guthabens: {e}")


# ============================================================
# 📊 ARBITRAGE SCANNER & TRADER LOGIK
# ============================================================


def scan_and_trade_arbitrage(exchanges):
    """Holt Preise ab, berechnet Spreads zwischen Börsen und führt bei Signal den Trade aus."""
    ex_names = list(exchanges.keys())
    pairs = list(itertools.permutations(ex_names, 2))

    for symbol in SYMBOLS_TO_SCAN:
        tickers = {}

        # 1. Ticker von allen Börsen abfragen
        for name, ex in exchanges.items():
            try:
                tickers[name] = ex.fetch_ticker(symbol)
            except Exception:
                continue

        # 2. Alle Kombinationen vergleichen (Börse A Kaufen -> Börse B Verkaufen)
        for buy_ex_name, sell_ex_name in pairs:
            if buy_ex_name not in tickers or sell_ex_name not in tickers:
                continue

            buy_price = tickers[buy_ex_name].get("ask")  # Kaufpreis (Ask)
            sell_price = tickers[sell_ex_name].get("bid")  # Verkaufspreis (Bid)

            if not buy_price or not sell_price or buy_price <= 0:
                continue

            # Marge berechnen in %
            spread_pct = ((sell_price - buy_price) / buy_price) * 100

            # Verbose-Logging: Zeige auch knappe Chancen an
            if spread_pct > 0.05:
                print(
                    f"🔍 {symbol} | Buy [{buy_ex_name.upper()} @ ${buy_price:.4f}] ➔ Sell [{sell_ex_name.upper()} @ ${sell_price:.4f}] | Spread: {spread_pct:+.2f}%"
                )

            # Execution-Trigger bei Erreichen der Marge
            if spread_pct >= MIN_PROFIT_THRESHOLD_PCT:
                print(
                    f"\n🚀 ARBITRAGE-SIGNAL: {symbol} (+{spread_pct:.2f}%)"
                )
                execute_arbitrage_trade(
                    exchanges[buy_ex_name],
                    exchanges[sell_ex_name],
                    symbol,
                    buy_price,
                    TRADE_AMOUNT_USDT,
                )


def execute_arbitrage_trade(
    buy_exchange, sell_exchange, symbol, buy_price, amount_usdt
):
    """Führt zeitgleich die Kauf- und Verkaufsorder auf den jeweiligen Börsen aus."""
    buy_name = buy_exchange.id.upper()
    sell_name = sell_exchange.id.upper()
    coin_amount = amount_usdt / buy_price

    print(
        f"⚡ Führe Trade aus: Kaufe {coin_amount:.4f} {symbol} auf {buy_name} & verkaufe auf {sell_name}..."
    )

    try:
        buy_order = buy_exchange.create_market_buy_order(symbol, coin_amount)
        print(f"✅ [{buy_name}] Kauf ausgeführt. Order-ID: {buy_order.get('id')}")
    except Exception as e:
        print(f"❌ [{buy_name}] Kauf fehlgeschlagen: {e}")
        return

    try:
        sell_order = sell_exchange.create_market_sell_order(
            symbol, coin_amount
        )
        print(
            f"✅ [{sell_name}] Verkauf ausgeführt. Order-ID: {sell_order.get('id')}"
        )
    except Exception as e:
        print(
            f"⚠️ [{sell_name}] Verkauf fehlgeschlagen! Coin muss über Auto-Cleanup verkauft werden. Fehler: {e}"
        )


# ============================================================
# 🔄 MAIN LOOP & TRADING ENGINE
# ============================================================


def run_trader():
    exchanges = init_exchanges()
    if not exchanges:
        print("❌ Keine Börsen geladen. Abbruch.")
        return

    print("✅ Börsen erfolgreich initialisiert!")

    # Vorab-Cleanup beim Start
    cleanup_altcoins_to_usdt(exchanges)

    print("\n============================================================")
    print("🚀 STARTE LIVE TRADING & SCANNING")
    print("============================================================")

    cycle = 0
    while True:
        cycle += 1
        print(f"\n--- Durchlauf #{cycle} ---")

        # Arbitrage Scannen und ausführen
        scan_and_trade_arbitrage(exchanges)

        # Periodischer Auto-Cleanup alle 10 Durchläufe
        if cycle % 10 == 0:
            cleanup_altcoins_to_usdt(exchanges)

        time.sleep(15)  # Scan-Intervall auf 15 Sekunden angepasst


if __name__ == "__main__":
    run_trader()
