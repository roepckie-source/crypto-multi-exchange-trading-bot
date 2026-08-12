import ccxt
import time

# Initialisiere Bitrue
EXCHANGE = ccxt.bitrue({
    "enableRateLimit": True,
    "timeout": 10000,
})

# Präzise Bitrue Standard-Gebühr für Maker/Taker (0.098% = 0.00098)
FEE_PER_TRADE = 0.00098  

# Erweiterte Liste: XRP, ETH, LTC + hocheffiziente Altcoins mit BTC-Märkten auf Bitrue
CANDIDATE_COINS = ["XRP", "ETH", "LTC", "BCH", "XLM", "VET"]

def get_btc_prices():
    """ Hält die Kompatibilität zur main.py Struktur aufrecht. """
    try:
        ticker = EXCHANGE.fetch_ticker("BTC/USDT")
        return {"bitrue": {"bid": float(ticker["bid"]), "ask": float(ticker["ask"])}}
    except Exception as e:
        print(f"⚠️ Bitrue Verbindungsfehler: {e}", flush=True)
        return {}

def find_best_opportunity(prices_dummy, trade_size=100.0):
    """ Scannt die Dreiecke: USDT -> COIN -> BTC -> USDT """
    try:
        # Lädt alle benötigten Ticker blitzschnell in einem einzigen Netzwerk-Request
        symbols_to_fetch = ([f"{c}/USDT" for c in CANDIDATE_COINS] + 
                             [f"{c}/BTC" for c in CANDIDATE_COINS] + 
                             ["BTC/USDT"])
        tickers = EXCHANGE.fetch_tickers(symbols_to_fetch)
    except Exception as e:
        print(f"❌ Fehler beim Laden der Bitrue-Ticker: {e}", flush=True)
        return None

    best_opp = None
    max_net_profit_percent = -999.0

    if "BTC/USDT" not in tickers: return None
    btc_usdt_bid = float(tickers["BTC/USDT"]["bid"])

    for coin in CANDIDATE_COINS:
        pair1 = f"{coin}/USDT"
        pair2 = f"{coin}/BTC"

        if pair1 not in tickers or pair2 not in tickers:
            continue

        try:
            # Schritt 1: USDT -> COIN (Kauf zum Ask-Preis)
            price1 = float(tickers[pair1]["ask"])
            if price1 <= 0: continue
            amount_coin = (trade_size / price1) * (1 - FEE_PER_TRADE)

            # Schritt 2: COIN -> BTC (Verkauf zum Bid-Preis)
            price2 = float(tickers[pair2]["bid"])
            if price2 <= 0: continue
            amount_btc = (amount_coin * price2) * (1 - FEE_PER_TRADE)

            # Schritt 3: BTC -> USDT (Verkauf zum Bid-Preis)
            end_usdt = (amount_btc * btc_usdt_bid) * (1 - FEE_PER_TRADE)

            # Netto-Rendite ermitteln
            net_profit_usd = end_usdt - trade_size
            net_profit_percent = (net_profit_usd / trade_size) * 100

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
        except Exception:
            continue

    return best_opp
