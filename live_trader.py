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

# Mindest-Gegenwert in USDT für den Altcoin-Auto-Cleanup (verhindert 'Min Notional'-Fehler der Börsen)
MIN_CLEANUP_VALUE_USDT = 5.0

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
                # Stablecoins & leere Guthaben überspringen
                if coin in ["USDT", "USD", "USDC"] or amount <= 0:
                    continue

                symbol = f"{coin}/USDT"

                # Prüfen, ob das Handelspaar auf der Börse existiert & Preis abrufen
                try:
                    ticker = ex.fetch_ticker(symbol)
                    current_price = ticker["last"]
                except Exception:
                    # Handelspaar existiert nicht auf dieser Börse
                    continue

                estimated_value_usdt = amount * current_price

                # Börsen verlangen meist 5-10 USDT Mindestwert für Orders (Dust Protection)
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
                    print(f"✅ [{ex_name}] Erfolgreich verkauft! Order-ID: {order_id}")
                except Exception as e:
                    print(f"❌ [{ex_name}] Fehler beim Verkauf von {coin}: {e}")

        except Exception as e:
            print(f"❌ [{ex_name}] Fehler beim Abrufen des Guthabens: {e}")


# ============================================================
# 🔄 MAIN LOOP & TRADING ENGINE
# ============================================================

def run_trader():
    exchanges = init_exchanges()
    if not exchanges:
        print("❌ Keine Börsen geladen. Abbruch.")
        return

    print("✅ Börsen erfolgreich initialisiert!")

    # 1. Vorab-Cleanup beim Start ausführen
    cleanup_altcoins_to_usdt(exchanges)

    print("\n============================================================")
    print("🚀 STARTE LIVE TRADING & SCANNING")
    print("============================================================")

    cycle = 0
    while True:
        cycle += 1
        print(f"\n--- Durchlauf #{cycle} ---")
        
        # Scanne Markt (Deine bestehende Arbitrage-Logik)
        # ... Arbitrage Scan Logik ...

        # Beispielsweiser periodischer Auto-Cleanup nach allen 10 Scans
        if cycle % 10 == 0:
            cleanup_altcoins_to_usdt(exchanges)

        time.sleep(60)


if __name__ == "__main__":
    run_trader()
