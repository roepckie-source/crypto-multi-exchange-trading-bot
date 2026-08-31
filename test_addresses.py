import os
import sys

try:
    import ccxt
except ImportError:
    print("❌ CCXT ist nicht installiert. Bitte mit 'pip install ccxt' installieren.")
    sys.exit(1)

# ============================================================
# ⚙️ BÖRSEN-INITIALISIERUNG
# ============================================================

def init_exchanges():
    exchanges = {}

    # 1. OKX (EEA EU-Fix)
    okx_key, okx_sec, okx_pass = os.getenv("OKX_API_KEY"), os.getenv("OKX_API_SECRET"), os.getenv("OKX_PASSPHRASE")
    if okx_key and okx_sec and okx_pass:
        exchanges["okx"] = ccxt.okx({
            "apiKey": okx_key, "secret": okx_sec, "password": okx_pass,
            "hostname": "my.okx.com", "enableRateLimit": True
        })

    # 2. MEXC
    mexc_key, mexc_sec = os.getenv("MEXC_API_KEY"), os.getenv("MEXC_API_SECRET")
    if mexc_key and mexc_sec:
        exchanges["mexc"] = ccxt.mexc({"apiKey": mexc_key, "secret": mexc_sec, "enableRateLimit": True})

    # 3. BITRUE
    bit_key, bit_sec = os.getenv("BITRUE_API_KEY"), os.getenv("BITRUE_API_SECRET")
    if bit_key and bit_sec:
        exchanges["bitrue"] = ccxt.bitrue({"apiKey": bit_key, "secret": bit_sec, "enableRateLimit": True})

    # 4. KUCOIN
    kuc_key, kuc_sec, kuc_pass = os.getenv("KUCOIN_API_KEY"), os.getenv("KUCOIN_API_SECRET"), os.getenv("KUCOIN_PASSPHRASE")
    if kuc_key and kuc_sec and kuc_pass:
        exchanges["kucoin"] = ccxt.kucoin({
            "apiKey": kuc_key, "secret": kuc_sec, "password": kuc_pass,
            "enableRateLimit": True
        })

    return exchanges

# ============================================================
# 🔍 TEST: USDT-EINZAHLUNGSADRESSEN ABRUFEN (TRX / TRC20)
# ============================================================

def test_deposit_addresses():
    print("🔍 STARTE ADRESS-TEST FOR USDT (NETZWERK: TRX / TRC20)...\n")
    exchanges = init_exchanges()

    if not exchanges:
        print("❌ Keine Börsen-Zugangsdaten in den Umgebungsvariablen gefunden.")
        return

    # Netzwerknamen je nach Börsen-API (CCXT mappt meist 'TRX' oder 'TRC20')
    network_params = {
        "okx": {"network": "TRX"},
        "mexc": {"network": "TRX"},
        "bitrue": {"network": "TRC20"},
        "kucoin": {"network": "TRX"}
    }

    for name, exchange in exchanges.items():
        params = network_params.get(name, {"network": "TRX"})
        try:
            deposit_info = exchange.fetch_deposit_address("USDT", params=params)
            
            address = deposit_info.get("address", "N/A")
            tag = deposit_info.get("tag", "Kein Tag/Memo nötig")
            
            print(f"✅ [{name.upper()}] Adresse erfolgreich abgerufen:")
            print(f"   📍 Adresse: {address}")
            if tag and tag != "Kein Tag/Memo nötig":
                print(f"   🏷️  Tag/Memo: {tag}")
            print("-" * 60)

        except Exception as e:
            print(f"❌ [{name.upper()}] Fehler beim Abrufen der Adresse:")
            print(f"   ⚠️  Details: {e}")
            print("-" * 60)

if __name__ == "__main__":
    test_deposit_addresses()
