import asyncio
import logging
from datetime import datetime
import ccxt.pro as ccxtpro

# --- LOGGING SETUP ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('paper_trading.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('PaperTrader')

# --- CONFIGURATION ---
MIN_24H_VOLUME_USDT = 50_000    # Mindestvolumen 24h
MAX_24H_VOLUME_USDT = 2_000_000  # Maximalvolumen 24h
TAKER_FEE = 0.001                # 0.1% Gebühr pro Trade
TRADE_SIZE_USDT = 100.0          # Festes Einsatzkapital pro Trade
MIN_PROFIT_THRESHOLD_PCT = 0.10  # Mindest-Nettoprofit für Ausführung (0.10%)


class PaperTradingEngine:
    """Simuliert Ausführungen und verwaltet die Performance-Statistik."""
    def __init__(self, initial_balance=1000.0):
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.total_trades = 0
        self.successful_trades = 0
        self.total_profit_usdt = 0.0

    def execute_trade(self, triangle, ask_a, bid_b, bid_c, profit_pct, final_usdt):
        profit_usdt = final_usdt - TRADE_SIZE_USDT
        
        self.total_trades += 1
        self.total_profit_usdt += profit_usdt
        self.current_balance += profit_usdt
        if profit_usdt > 0:
            self.successful_trades += 1

        win_rate = (self.successful_trades / self.total_trades) * 100

        logger.info("=" * 60)
        logger.info(f"SIMULIERTER TRADE #{self.total_trades} | Asset: {triangle['base']}")
        logger.info(f"  1. Buy  {triangle['pair_a']} @ {ask_a:.6f}")
        logger.info(f"  2. Sell {triangle['pair_b']} @ {bid_b:.8f}")
        logger.info(f"  3. Sell {triangle['pair_c']} @ {bid_c:.2f}")
        logger.info(f"  Rendite: {profit_pct:+.3f}% | Netto-Gewinn: {profit_usdt:+.4f} USDT")
        logger.info(f"  Gesamtsaldo: {self.current_balance:.2f} USDT (P/L Gesamt: {self.total_profit_usdt:+.2f} USDT | Win-Rate: {win_rate:.1f}%)")
        logger.info("=" * 60)


async def get_filtered_small_cap_triangles(exchange):
    """Filtert Nischen-Handelspaare im angegebenen 24h-Volumenbereich."""
    await exchange.load_markets()
    tickers = await exchange.fetch_tickers()
    
    usdt_pairs = {}
    btc_pairs = {}
    
    for symbol, ticker in tickers.items():
        quote_volume = ticker.get('quoteVolume', 0) or 0
        market = exchange.markets.get(symbol)
        
        if not market or not market['active']:
            continue
            
        base = market['base']
        quote = market['quote']
        
        if MIN_24H_VOLUME_USDT <= quote_volume <= MAX_24H_VOLUME_USDT:
            if quote == 'USDT':
                usdt_pairs[base] = symbol
            elif quote == 'BTC':
                btc_pairs[base] = symbol

    common_bases = set(usdt_pairs.keys()) & set(btc_pairs.keys())
    major_coins = {'BTC', 'ETH', 'SOL', 'XRP', 'BNB', 'USDC', 'ADA', 'DOGE'}
    filtered_bases = common_bases - major_coins

    triangles = []
    for base in filtered_bases:
        triangles.append({
            'base': base,
            'pair_a': usdt_pairs[base],
            'pair_b': btc_pairs[base],
            'pair_c': 'BTC/USDT'
        })
        
    logger.info(f"Small-Cap-Dreiecke gefunden: {len(triangles)}")
    return triangles


def check_orderbook_depth(ask_price, ask_qty, bid_price, bid_qty, trade_size_usdt):
    """Prüft, ob ausreichend Volumen auf Level 1 liegt."""
    ask_value_usdt = ask_price * ask_qty
    bid_value_usdt = bid_price * bid_qty
    return ask_value_usdt >= trade_size_usdt and bid_value_usdt >= trade_size_usdt


async def monitor_and_paper_trade():
    exchange = ccxtpro.kucoin({'enableRateLimit': True})
    paper_trader = PaperTradingEngine(initial_balance=1000.0)
    
    try:
        triangles = await get_filtered_small_cap_triangles(exchange)
        
        if not triangles:
            logger.warning("Keine passenden Dreiecke gefunden.")
            return

        logger.info("Starte Überwachung und Paper Trading...")
        
        while True:
            for t in triangles[:15]:  # Überwacht die Top 15 gefilterten Dreiecke
                try:
                    ob_a = await exchange.fetch_order_book(t['pair_a'])
                    ob_b = await exchange.fetch_order_book(t['pair_b'])
                    ob_c = await exchange.fetch_order_book(t['pair_c'])
                    
                    if not (ob_a['asks'] and ob_b['bids'] and ob_c['bids']):
                        continue
                    
                    ask_a, qty_a = ob_a['asks'][0][0], ob_a['asks'][0][1]
                    bid_b, qty_b = ob_b['bids'][0][0], ob_b['bids'][0][1]
                    bid_c, qty_c = ob_c['bids'][0][0], ob_c['bids'][0][1]

                    # 1. Liquiditäts-Check
                    if not check_orderbook_depth(ask_a, qty_a, bid_b, qty_b, TRADE_SIZE_USDT):
                        continue

                    # 2. Dreiecksrechnung (3 Trades inkl. Taker Fees)
                    coin_amount = (TRADE_SIZE_USDT / ask_a) * (1 - TAKER_FEE)
                    btc_amount = (coin_amount * bid_b) * (1 - TAKER_FEE)
                    final_usdt = (btc_amount * bid_c) * (1 - TAKER_FEE)

                    profit_pct = ((final_usdt - TRADE_SIZE_USDT) / TRADE_SIZE_USDT) * 100

                    # 3. Paper-Trade ausführen, wenn Schwelle erreicht
                    if profit_pct >= MIN_PROFIT_THRESHOLD_PCT:
                        paper_trader.execute_trade(t, ask_a, bid_b, bid_c, profit_pct, final_usdt)
                
                except Exception:
                    continue

            await asyncio.sleep(1)

    except Exception as e:
        logger.error(f"Fehler im Ablauf: {e}")
    finally:
        await exchange.close()

if __name__ == '__main__':
    asyncio.run(monitor_and_paper_trade())
