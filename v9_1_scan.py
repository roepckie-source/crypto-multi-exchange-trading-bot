import time
from web3 import Web3
from v9_config import RPC_HTTP
from v9_dex_scanner import DexScanner

def main():
    w3=Web3(Web3.HTTPProvider(RPC_HTTP,request_kwargs={"timeout":10}))
    if not w3.is_connected():raise RuntimeError("RPC connection failed")
    if w3.eth.chain_id!=4663:raise RuntimeError(f"Unexpected chain ID: {w3.eth.chain_id}")
    dex=DexScanner(w3)
    if not dex.factory_code_present():raise RuntimeError("Uniswap V3 factory has no code")
    last=w3.eth.block_number
    print("V9.1 DEX / LIQUIDITY SCANNER — PAPER ONLY")
    print(f"chain_id={w3.eth.chain_id} factory={dex.factory.address} block={last}")
    while True:
        cur=w3.eth.block_number
        if cur>last:
            for p in dex.find_new_pools(last+1,cur):
                print(f"[NEW POOL] block={p.block_number} {p.token0_symbol or '?'} / {p.token1_symbol or '?'} fee={p.fee} pool={p.pool}")
                print(f"           liquidity_raw={p.liquidity_raw} tick={p.tick} sqrtPriceX96={p.sqrt_price_x96}")
                print("[PAPER] detection only; no position opened.")
            last=cur
        time.sleep(2)
if __name__=="__main__":main()
