from dataclasses import dataclass
from web3 import Web3

UNISWAP_V3_FACTORY=Web3.to_checksum_address("0x1f7d7550b1b028f7571e69a784071f0205fd2efa")
FACTORY_ABI=[{"anonymous":False,"inputs":[{"indexed":True,"name":"token0","type":"address"},{"indexed":True,"name":"token1","type":"address"},{"indexed":False,"name":"fee","type":"uint24"},{"indexed":False,"name":"tickSpacing","type":"int24"},{"indexed":False,"name":"pool","type":"address"}],"name":"PoolCreated","type":"event"}]
ERC20_ABI=[
{"inputs":[],"name":"symbol","outputs":[{"type":"string"}],"stateMutability":"view","type":"function"},
{"inputs":[],"name":"decimals","outputs":[{"type":"uint8"}],"stateMutability":"view","type":"function"},
{"inputs":[],"name":"totalSupply","outputs":[{"type":"uint256"}],"stateMutability":"view","type":"function"}]
POOL_ABI=[
{"inputs":[],"name":"liquidity","outputs":[{"type":"uint128"}],"stateMutability":"view","type":"function"},
{"inputs":[],"name":"slot0","outputs":[{"type":"uint160"},{"type":"int24"},{"type":"uint16"},{"type":"uint16"},{"type":"uint16"},{"type":"uint8"},{"type":"bool"}],"stateMutability":"view","type":"function"}]

@dataclass
class PoolCandidate:
    pool:str; token0:str; token1:str; fee:int; block_number:int; tx_hash:str
    token0_symbol:str|None=None; token1_symbol:str|None=None
    token0_decimals:int|None=None; token1_decimals:int|None=None
    liquidity_raw:int|None=None; sqrt_price_x96:int|None=None; tick:int|None=None

class DexScanner:
    def __init__(self,w3):
        self.w3=w3
        self.factory=w3.eth.contract(address=UNISWAP_V3_FACTORY,abi=FACTORY_ABI)
    def factory_code_present(self):
        return bool(self.w3.eth.get_code(UNISWAP_V3_FACTORY))
    def find_new_pools(self,lo,hi):
        if lo>hi:return []
        events=self.factory.events.PoolCreated.get_logs(from_block=lo,to_block=hi)
        out=[]
        for e in events:
            a=e["args"]; c=PoolCandidate(
                Web3.to_checksum_address(a["pool"]),
                Web3.to_checksum_address(a["token0"]),
                Web3.to_checksum_address(a["token1"]),
                int(a["fee"]),int(e["blockNumber"]),e["transactionHash"].hex())
            self._enrich(c); out.append(c)
        return out
    def _enrich(self,c):
        for i,address in enumerate((c.token0,c.token1)):
            t=self.w3.eth.contract(address=address,abi=ERC20_ABI)
            try:s=t.functions.symbol().call()
            except Exception:s=None
            try:d=int(t.functions.decimals().call())
            except Exception:d=None
            if i==0:c.token0_symbol,c.token0_decimals=s,d
            else:c.token1_symbol,c.token1_decimals=s,d
        p=self.w3.eth.contract(address=c.pool,abi=POOL_ABI)
        try:c.liquidity_raw=int(p.functions.liquidity().call())
        except Exception:pass
        try:
            s=p.functions.slot0().call(); c.sqrt_price_x96=int(s[0]); c.tick=int(s[1])
        except Exception:pass
