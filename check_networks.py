import os
import ccxt

def check_usdt_networks():
    print("🔍 Prüfe unterstützte USDT-Netzwerke & Gebühren...\n")

    # Initialisierung der Börsen (OKX mit EU-Fix)
    exchanges = {
        "okx": ccxt.okx({
            "apiKey": os.getenv("OKX_API_KEY"),
            "secret": os.getenv("OKX_API_SECRET"),
            "password": os.getenv("OKX_PASSPHRASE"),
            "hostname": "my.okx.com",
        }),
        "mexc": ccxt.mexc({
            "apiKey": os.getenv("MEXC_API_KEY"),
            "secret": os.getenv("MEXC_API_SECRET"),
        }),
        "bitrue": ccxt.bitrue({
            "apiKey": os.getenv("BITRUE_API_KEY"),
            "secret": os.getenv("BITRUE_API_SECRET"),
        })
    }

    networks_by_exchange = {}

    for name, ex in exchanges.items():
        try:
            # Währungsinformationen abrufen
            currencies = ex.fetch_currencies()
            usdt_info = currencies.get("USDT", {})
            networks = usdt_info.get("networks", {})

            networks_by_exchange[name] = {}

            for net_id, net_data in networks.items():
                # Status & Gebühren auslesen
                active = net_data.get("active", True)
                withdraw_enabled = net_data.get("withdraw", True)
                fee = net_data.get("fee", None)

                if active and withdraw_enabled:
                    networks_by_exchange[name][net_id.upper()] = fee

        except Exception as e:
            print(f"❌ Fehler beim Abfragen von {name.upper()}: {e}")

    # Schnittmenge aller unterstützen Netzwerke ermitteln
    all_sets = [set(nets.keys()) for nets in networks_by_exchange.values() if nets]
    
    if not all_sets:
        print("❌ Keine Netzwerkinformationen gefunden.")
        return

    common_networks = set.intersection(*all_sets)

    print("=" * 60)
    print("🟢 GEMEINSAM UNTERSTÜTZTE USDT-NETZWERKE")
    print("=" * 60)

    if not common_networks:
        print("⚠️ Keine überschneidenden Netzwerke gefunden.")
        return

    for net in sorted(common_networks):
        okx_fee = networks_by_exchange["okx"].get(net, "N/A")
        mexc_fee = networks_by_exchange["mexc"].get(net, "N/A")
        bitrue_fee = networks_by_exchange["bitrue"].get(net, "N/A")

        print(f"\n🌐 Netzwerk: {net}")
        print(f"  ├─ OKX Fee:    {okx_fee} USDT")
        print(f"  ├─ MEXC Fee:   {mexc_fee} USDT")
        print(f"  └─ Bitrue Fee: {bitrue_fee} USDT")

if __name__ == "__main__":
    check_usdt_networks()
