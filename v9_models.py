from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TokenCandidate:
    address: str
    block_number: int
    tx_hash: str
    deployer: Optional[str] = None
    name: Optional[str] = None
    symbol: Optional[str] = None
    decimals: Optional[int] = None
    total_supply: Optional[int] = None
    created_at_ms: Optional[int] = None

    liquidity_usdt: Optional[float] = None
    top_holder_share_pct: Optional[float] = None
    dev_share_pct: Optional[float] = None

    mint_authority_risk: bool = False
    blacklist_risk: bool = False
    pause_risk: bool = False
    tax_risk: bool = False
    liquidity_risk: bool = False

    smart_money_score: float = 0.0
    contract_score: float = 0.0
    liquidity_score: float = 0.0
    wallet_score: float = 0.0
    total_score: float = 0.0
    decision: str = "SKIP"

    reasons: list[str] = field(default_factory=list)


@dataclass
class PaperPosition:
    token: str
    entry_price: float
    quantity: float
    entry_time_ms: int
    score: float


@dataclass
class PaperTrade:
    token: str
    entry_price: float
    exit_price: float
    quantity: float
    pnl_usdt: float
    entry_time_ms: int
    exit_time_ms: int
    score: float
    decision_reason: str
