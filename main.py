print("🔥 TEST MAIN.PY START", flush=True)

print("🔥 ZEILE 1", flush=True)
print("🔥 ZEILE 2", flush=True)

from market_scanner import get_btc_prices

print("✅ market_scanner IMPORTIERT", flush=True)

print("📡 STARTE BTC PREISABFRAGE", flush=True)

prices = get_btc_prices()

print("✅ PREISE ZURÜCK", flush=True)
print(prices, flush=True)

print("🏁 MAIN.PY ENDE", flush=True)
