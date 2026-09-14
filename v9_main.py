from __future__ import annotations

import time
from web3 import Web3

from v9_config import RPC_HTTP, STARTING_PAPER_USDT, PAPER_POSITION_USDT
from v9_launch_scanner import find_created_contracts
from v9_risk_engine import evaluate
from v9_storage import V9Storage
from v9_paper_sniper import PaperSniper
from v9_wallet_intelligence import WalletIntelligence


def main():
    if not RPC_HTTP:
        raise RuntimeError("Set RPC_HTTP in v9_config.py")

    w3 = Web3(Web3.HTTPProvider(RPC_HTTP, request_kwargs={"timeout": 10}))
    if not w3.is_connected():
        raise RuntimeError("Could not connect to Robinhood Chain RPC")

    storage = V9Storage()
    wallets = WalletIntelligence()
    sniper = PaperSniper(STARTING_PAPER_USDT, PAPER_POSITION_USDT)

    last_block = w3.eth.block_number

    print("=" * 88)
    print("V9 MEME SNIPER / ON-CHAIN INTELLIGENCE")
    print("ROBINHOOD CHAIN | PAPER ONLY | NO LIVE ORDERS")
    print("=" * 88)
    print(f"chain_id={w3.eth.chain_id}")
    print(f"starting_block={last_block}")

    while True:
        current = w3.eth.block_number

        while last_block < current:
            last_block += 1
            print(f"[BLOCK] {last_block}")

            try:
                candidates = find_created_contracts(w3, last_block)
            except Exception as exc:
                print(f"[SCAN ERROR] block={last_block} error={exc}")
                continue

            for token in candidates:
                token.wallet_score = wallets.score_token(token.address)
                token = evaluate(token)
                storage.save_token(token)

                print(
                    f"[TOKEN] {token.symbol or '?':<12} "
                    f"{token.address} "
                    f"score={token.total_score:5.1f} "
                    f"decision={token.decision} "
                    f"reasons={','.join(token.reasons) or 'none'}"
                )

                # No market price is assumed here. A real paper entry requires
                # a verified DEX quote module, which is the next stage.
                if token.decision == "PAPER_BUY":
                    print(
                        "[PAPER] candidate accepted by risk engine; "
                        "DEX quote not configured, so NO position opened."
                    )

        print(sniper.summary())
        time.sleep(2)


if __name__ == "__main__":
    main()
