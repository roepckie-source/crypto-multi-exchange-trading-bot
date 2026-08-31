import os
import sys
import time

# CCXT-Bibliothek für Börsenzugriff laden
try:
    import ccxt
except ImportError:
    ccxt = None

# ============================================================
# ⚙️ BÖRSEN-INITIALISIERUNG (REBALANCER)
# ============================================================


def init_exchanges():
    """Initialisiert die Börsenverbindungen für das Rebalancing."""
    exchanges = {}

    if not ccxt:
        print("⚠️ CCXT ist nicht installiert!")
        return exchanges

    # 1. OKX Initialisierung (Inklusive EEA-Fix für EU-Konten)
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
                    "hostname": "my.okx.com",  # Fix für EU/EEA-Accounts (Fehler 50119)
                    "enableRateLimit": True,
                }
            )
        except Exception as e:
            print(f"❌ Fehler bei der Initialisierung von OKX: {e}")

    # 2. MEXC Initialisierung
    mexc_key = os.getenv("MEXC_API_KEY")
    mexc_secret = os.getenv("MEXC_API_SECRET")

    if mexc_key and mexc_secret:
        try:
            exchanges["mexc"] = ccxt.mexc(
                {"apiKey": mexc_key, "secret": mexc_secret, "enableRateLimit": True}
            )
        except Exception as e:
            print(f"❌ Fehler bei der Initialisierung von MEXC: {e}")

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
            print(f"❌ Fehler bei der Initialisierung von BITRUE: {e}")

    # 4. KuCoin Initialisierung
    kucoin_key = os.getenv("KUCOIN_API_KEY")
    kucoin_secret = os.getenv("KUCOIN_API_SECRET")
    kucoin_passphrase = os.getenv("KUCOIN_PASSPHRASE")

    if kucoin_key and kucoin_secret and kucoin_passphrase:
        try:
            exchanges["kucoin"] = ccxt.kucoin(
                {
                    "apiKey": kucoin_key,
                    "secret": kucoin_secret,
                    "password": kucoin_passphrase,
                    "enableRateLimit": True,
                }
            )
        except Exception as e:
            print(f"❌ Fehler bei der Initialisierung von KuCoin: {e}")

    return exchanges


# ============================================================
# ⚖️ REBALANCING-PRÜFUNG
# ============================================================


def check_and_rebalance():
    """Liest Guthaben aller Börsen aus und gibt Übersicht aus."""
    print("⚖️ Starte Rebalancing-Prüfung...")

    exchanges = init_exchanges()
    if not exchanges:
        print("❌ Keine gültigen Börsen-Verbindungen gefunden.")
        return

    balances = {}

    for name, exchange in exchanges.items():
        try:
            balance_data = exchange.fetch_balance()

            # Abfragen des verfügbaren USDT-Guthabens
            usdt_free = 0.0
            if "USDT" in balance_data:
                usdt_free = float(balance_data["USDT"].get("free", 0.0))
            elif "free" in balance_data and "USDT" in balance_data["free"]:
                usdt_free = float(balance_data["free"]["USDT"])

            balances[name] = usdt_free
            print(f"💰 [{name.upper()}] Verfügbares USDT: {usdt_free:.2f}")

        except Exception as e:
            print(f"❌ Fehler beim Abfragen von {name}: {e}")

    # Auswertung des Gesamt-Guthabens
    if balances:
        total_usdt = sum(balances.values())
        avg_usdt = total_usdt / len(balances)

        print("\n" + "=" * 50)
        print(f"📊 REBALANCING ZUSAMMENFASSUNG")
        print(f"Gesamt-USDT über alle aktiven Börsen: ${total_usdt:.2f}")
        print(f"Ziel-Guthaben pro Börse:             ${avg_usdt:.2f}")
        print("=" * 50)


if __name__ == "__main__":
    check_and_rebalance()
