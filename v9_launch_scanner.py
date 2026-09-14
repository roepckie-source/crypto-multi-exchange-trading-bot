from __future__ import annotations

import time
from web3 import Web3

from v9_config import MAX_NEW_CONTRACTS_PER_BLOCK
from v9_contract_analyzer import analyze_contract
from v9_models import TokenCandidate


def find_created_contracts(w3: Web3, block_number: int) -> list[TokenCandidate]:
    """
    Find contracts created by transactions in a block.

    This is intentionally chain-generic. It does not assume a specific DEX
    factory address. DEX launch detection is added after verified factory/
    router deployments are configured.
    """
    block = w3.eth.get_block(block_number, full_transactions=True)
    candidates = []

    for tx in block.transactions[:MAX_NEW_CONTRACTS_PER_BLOCK]:
        # Contract creation transactions have `to == None`.
        if tx.get("to") is not None:
            continue

        receipt = w3.eth.get_transaction_receipt(tx["hash"])
        created = receipt.get("contractAddress")
        if not created:
            continue

        try:
            analysis = analyze_contract(w3, created)
        except Exception:
            continue

        if not analysis.valid_erc20:
            continue

        candidates.append(
            TokenCandidate(
                address=created,
                block_number=block_number,
                tx_hash=tx["hash"].hex(),
                deployer=tx["from"],
                name=analysis.name,
                symbol=analysis.symbol,
                decimals=analysis.decimals,
                total_supply=analysis.total_supply,
                created_at_ms=int(time.time() * 1000),
                contract_score=analysis.score,
                mint_authority_risk=analysis.mint_risk,
                blacklist_risk=analysis.blacklist_risk,
                pause_risk=analysis.pause_risk,
                tax_risk=analysis.tax_risk,
            )
        )

    return candidates
