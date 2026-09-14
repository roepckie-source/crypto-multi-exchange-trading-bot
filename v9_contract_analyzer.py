from __future__ import annotations

from dataclasses import dataclass
from web3 import Web3


@dataclass
class ContractAnalysis:
    valid_erc20: bool
    name: str | None
    symbol: str | None
    decimals: int | None
    total_supply: int | None
    mint_risk: bool
    blacklist_risk: bool
    pause_risk: bool
    tax_risk: bool
    score: float
    reasons: list[str]


ERC20_ABI = [
    {
        "constant": True,
        "inputs": [],
        "name": "name",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "totalSupply",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
    },
]


def analyze_contract(w3: Web3, address: str) -> ContractAnalysis:
    address = w3.to_checksum_address(address)
    code = w3.eth.get_code(address)

    if not code or code == b"\x00":
        return ContractAnalysis(
            False, None, None, None, None,
            True, True, True, True, 0.0,
            ["NO_CONTRACT_CODE"],
        )

    token = w3.eth.contract(address=address, abi=ERC20_ABI)
    reasons = []
    score = 40.0

    def call(fn, fallback=None):
        try:
            return fn.call()
        except Exception:
            return fallback

    name = call(token.functions.name())
    symbol = call(token.functions.symbol())
    decimals = call(token.functions.decimals())
    total_supply = call(token.functions.totalSupply())

    if name and symbol and decimals is not None and total_supply is not None:
        score += 35
    else:
        reasons.append("ERC20_METADATA_INCOMPLETE")
        score -= 15

    # Static bytecode heuristics are intentionally conservative.
    # They are NOT a substitute for verified-source analysis.
    bytecode = code.hex().lower()

    mint_risk = "40c10f19" in bytecode  # mint(address,uint256)
    blacklist_risk = False
    pause_risk = "8456cb59" in bytecode  # pause()
    tax_risk = False

    if mint_risk:
        reasons.append("MINT_FUNCTION_SIGNATURE_PRESENT")
        score -= 25

    if pause_risk:
        reasons.append("PAUSE_FUNCTION_SIGNATURE_PRESENT")
        score -= 10

    score = max(0.0, min(100.0, score))

    return ContractAnalysis(
        True, name, symbol, decimals, total_supply,
        mint_risk, blacklist_risk, pause_risk, tax_risk,
        score, reasons,
    )
