from market_scanner import get_btc_prices, find_best_opportunity

print("🚀 BTC ARBITRAGE SCANNER START", flush=True)

print("🔎 Hole aktuelle BTC-Preise...", flush=True)

prices = get_btc_prices()

print(
f"✅ {len(prices)} Börsen erfolgreich abgefragt",
flush=True
)

opportunity = find_best_opportunity(prices)

print("=" * 65, flush=True)

print("🧠 BTC REAL ORDERBOOK ANALYSIS", flush=True)

if opportunity is None:
print("🔴 Keine profitable Arbitrage gefunden", flush=True)
else:
print(
f"🟢 Kaufen: {opportunity['buy_exchange'].upper()}",
flush=True
)

```
print(
    f"🔴 Verkaufen: {opportunity['sell_exchange'].upper()}",
    flush=True
)

print(
    f"💰 Netto: {opportunity['net_profit_percent']:.4f}%",
    flush=True
)

print(
    f"💵 Gewinn: ${opportunity['net_profit']:,.4f}",
    flush=True
)
```

print("=" * 65, flush=True)

print("🏁 SCAN ABGESCHLOSSEN", flush=True)
