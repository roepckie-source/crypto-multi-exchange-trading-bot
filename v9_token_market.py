from dataclasses import dataclass

@dataclass
class MarketSnapshot:
    pool:str; token0:str; token1:str; symbol0:str|None; symbol1:str|None
    fee:int; liquidity_raw:int|None; sqrt_price_x96:int|None; tick:int|None
    price_token1_per_token0:float|None

def sqrt_price_to_price(sqrt_price_x96,decimals0=None,decimals1=None):
    if not sqrt_price_x96:return None
    raw=(sqrt_price_x96/(2**96))**2
    if decimals0 is None or decimals1 is None:return raw
    return raw*(10**decimals0)/(10**decimals1)

def build_snapshot(pool):
    return MarketSnapshot(pool.pool,pool.token0,pool.token1,pool.token0_symbol,pool.token1_symbol,
        pool.fee,pool.liquidity_raw,pool.sqrt_price_x96,pool.tick,
        sqrt_price_to_price(pool.sqrt_price_x96,pool.token0_decimals,pool.token1_decimals))
