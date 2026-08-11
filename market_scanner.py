import ccxt
import time

# Initialisiere Bitrue
EXCHANGE = ccxt.bitrue({
    "enableRateLimit": True,
    "timeout": 10000,
})

# Wir nutzen Standard-Gebühren von Bitrue (0.098% für die meisten Paare)
# Da wir 3 Trades im Kreis machen: 3 * 0.00098 = ca. 0.294% Gesamtgebühren
FEE_PER_TRADE = 0.00098  

# Coins, die stabil genug sind und hohes Volumen auf Bitrue haben
CANDIDATE_COINS = ["XRP", "SOL", "ADA", "DOGE", "LINK", "LTC", "ETH", "DOT", "MATIC"]

def get_btc_prices():
    """
    Dummy-Funktion zur Aufrechterhaltung der Kompatibilität mit der main.py Struktur.
    Gibt Bitrue als aktiven Status zurück.
    """
    try:
        ticker = EXCHANGE.fetch_ticker("BTC/USDT")
        return {"bitrue": {"bid": float(ticker["bid"]), "ask": float(ticker["ask"])}}
    except Exception as e:
        print(f"⚠️ Bitrue Verbindungsfehler: {e}", flush=True)
        return {}

def find_best_opportunity(prices_dummy, trade_size=100.0):
    """
    Scannt die Dreiecks-Kombinationen auf Bitrue:
    USDT -> COIN -> BTC -> USDT
    """
    print("\n🔎 Starte Dreiecks-Arbitrage-Analyse auf BITRUE...", flush=True)
    
    try:
        # Lade alle Ticker zeitgleich, um Netzwerklatenz zu minimieren
        tickers = EXCHANGE.fetch_tickers([f"{c}/USDT" for c in CANDIDATE_COINS] + 
                                          [f"{c}/BTC" for c in CANDIDATE_COINS] + 
                                          ["BTC/USDT"])
    except Exception as e:
        print(f"❌ Fehler beim Laden der Bitrue-Ticker: {e}", flush=True)
        return None

    best_opp = None
    max_net_profit_percent = -999.0

    # Basis-Markt BTC/USDT abgreifen
    if "BTC/USDT" not in tickers: return None
    btc_usdt_bid = float(tickers["BTC/USDT"]["bid"])

    for coin in CANDIDATE_COINS:
        pair1 = f"{coin}/USDT"
        pair2 = f"{coin}/BTC"

        if pair1 not in tickers or pair2 not in tickers:
            continue

        # Schritt 1: USDT -> COIN (Wir KAUFEN den Coin mit USDT zum 'ask'-Preis)
        price1 = float(tickers[pair1]["ask"])
        if price1 <= 0: continue
        amount_coin = trade_size / price1
        amount_coin_after_fee = amount_coin * (1 - FEE_PER_TRADE)

        # Schritt 2: COIN -> BTC (Wir VERKAUFEN den Coin gegen BTC zum 'bid'-Preis)
        price2 = float(tickers[pair2]["bid"])
        if price2 <= 0: continue
        amount_btc = amount_coin_after_fee * price2
        amount_btc_after_fee = amount_btc * (1 - FEE_PER_TRADE)

        # Schritt 3: BTC -> USDT (Wir VERKAUFEN das BTC zurück in USDT zum 'bid'-Preis)
        end_usdt = amount_btc_after_fee * btc_usdt_bid
        end_usdt_after_fee = end_usdt * (1 - FEE_PER_TRADE)

        # Profit-Berechnung
        net_profit_usd = end_usdt_after_fee - trade_size
        net_profit_percent = (net_profit_usd / trade_size) * 100

        # Debug-Anzeige für den Log
        print(f"🔄 Pfad: USDT -> {coin:5} -> BTC -> USDT | Netto: {net_profit_percent:+.4f}%", flush=True)

        if net_profit_percent > max_net_profit_percent:
            max_net_profit_percent = net_profit_percent
            best_opp = {
                "buy_exchange": "bitrue",
                "sell_exchange": f"triangular_{coin}",
                "buy_price": price1,
                "sell_price": price2,
                "net_profit": round(net_profit_usd, 4),
                "net_profit_percent": round(net_profit_percent, 4),
                "trade_size": trade_size,
                "coin": coin
            }

    return best_opp
