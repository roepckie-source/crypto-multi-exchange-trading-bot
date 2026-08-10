from market_scanner import get_btc_prices, find_best_opportunity

print("🚀 BTC ARBITRAGE SCANNER START", flush=True)

print("\n🔎 Hole aktuelle BTC-Preise...", flush=True)

prices = get_btc_prices()

print(
f"\n✅ {len(prices)} Börsen erfolgreich abgefragt",
flush=True
)

if prices:
print("\n🧠 Starte echte Orderbuch-Analyse...", flush=True)

```
opportunity = find_best_opportunity(prices)

print("\n" + "=" * 65, flush=True)

if opportunity:
    print("✅ BESTE ARBITRAGE-CHANCE", flush=True)

    print(
        f"Kaufen:    {opportunity['buy_exchange'].upper()}",
        flush=True
    )

    print(
        f"Verkaufen: {opportunity['sell_exchange'].upper()}",
        flush=True
    )

    print(
        f"Netto:     {opportunity['net_profit_percent']:.4f}%",
        flush=True
    )

    print(
        f"Gewinn:    ${opportunity['net_profit']:,.4f}",
        flush=True
    )

else:
    print(
        "🔴 Keine profitable Arbitrage gefunden",
        flush=True
    )

print("=" * 65, flush=True)
```

else:
print(
"❌ Keine Börsendaten erhalten",
flush=True
)

print("\n🏁 Scan abgeschlossen", flush=True)
