#!/usr/bin/env python3
import os
import ccxt

def init_exchanges():
    exchanges = {}
    
    okx_key = os.getenv("OKX_API_KEY")
    if okx_key:
        exchanges['okx'] = ccxt.okx({
            'apiKey': okx_key,
            'secret': os.getenv("OKX_API_SECRET"),
            'password': os.getenv("OKX_PASSPHRASE"),
            'enableRateLimit': True,
        })

    mexc_key = os.getenv("MEXC_API_KEY")
    if mexc_key:
        exchanges['mexc'] = ccxt.mexc({
            'apiKey': mexc_key,
            'secret': os.getenv("MEXC_API_SECRET"),
            'enableRateLimit': True,
        })

    bitrue_key = os.getenv("BITRUE_API_KEY")
    if bitrue_key:
        exchanges['bitrue'] = ccxt.bitrue({
            'apiKey': bitrue_key,
            'secret': os.getenv("BITRUE_API_SECRET"),
            'enableRateLimit': True,
        })

    return exchanges

def check_and_rebalance():
    exchanges = init_exchanges()
    print("⚖️ Starte Rebalancing-Prüfung...")

    # Coins, die wir bei Schieflagen liquidated / rebalancen wollen
    REBALANCE_COINS = ["RVN", "FLOKI", "DGB"]
    MIN_USDT_THRESHOLD = 5.0  # Mindest-USDT Schwelle für Alarm/Aktion

    balances = {}
    for ex_name, ex in exchanges.items():
        try:
            bal = ex.fetch_balance()
            usdt_free = bal['free'].get('USDT', 0.0) or bal['total'].get('USDT', 0.0)
            balances[ex_name] = {'USDT': usdt_free, 'instance': ex, 'full_bal': bal}
            print(f"💰 [{ex_name.upper()}] Verfügbares USDT: {usdt_free:.2f}")
        except Exception as e:
            print(f"❌ Fehler beim Abfragen von {ex_name}: {e}")

    # Prüfung: Gibt es eine Börse mit zu wenig USDT?
    for ex_name, data in balances.items():
        if data['USDT'] < MIN_USDT_THRESHOLD:
            print(f"⚠️ [{ex_name.upper()}] USDT-Stand niedrig ({data['USDT']:.2f} USDT). Suche nach verkaufbaren Altcoins...")
            
            ex = data['instance']
            full_bal = data['full_bal']
            
            for coin in REBALANCE_COINS:
                coin_amount = full_bal['free'].get(coin, 0.0) or full_bal['total'].get(coin, 0.0)
                if coin_amount > 0:
                    symbol = f"{coin}/USDT"
                    try:
                        ticker = ex.fetch_ticker(symbol)
                        bid_price = ticker.get('bid', 0)
                        val_usd = coin_amount * bid_price
                        
                        # Nur verkaufen, wenn der Gegenwert mindestens 2 USD beträgt
                        if val_usd >= 2.0:
                            print(f"🔄 [{ex_name.upper()}] Verkaufe {coin_amount:.2f} {coin} (~{val_usd:.2f} USD) gegen USDT...")
                            sell_order = ex.create_market_sell_order(symbol, coin_amount)
                            print(f"✅ Rebalancing-Verkauf erfolgreich: Order-ID {sell_order.get('id')}")
                    except Exception as e:
                        print(f"❌ Rebalancing-Verkauf für {symbol} auf {ex_name} fehlgeschlagen: {e}")

if __name__ == "__main__":
    check_and_rebalance()
