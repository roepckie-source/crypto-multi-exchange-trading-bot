
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class WalletProfile:
    address: str
    launches_seen: int = 0
    early_entries: int = 0
    wins: int = 0
    losses: int = 0
    realized_pnl: float = 0.0
    total_entry_cost: float = 0.0
    closed_trades: int = 0
    _seen_tokens: set[str] = field(default_factory=set, repr=False)
    _seen_trade_ids: set[str] = field(default_factory=set, repr=False)

    @property
    def win_rate(self) -> float:
        """Bayesian win rate with five neutral prior observations."""
        return (self.wins + 2.5) / (self.closed_trades + 5.0)

    @property
    def realized_roi(self) -> float:
        if self.total_entry_cost <= 0:
            return 0.0
        return self.realized_pnl / self.total_entry_cost

    @property
    def score(self) -> float:
        if self.launches_seen == 0:
            return 0.0

        # A small sample must not look like proven skill.
        confidence = min(1.0, self.closed_trades / 20.0)

        early_rate = self.early_entries / self.launches_seen

        # ROI score: 0 at -25% ROI, 50 at 0%, 100 at +25%.
        roi_score = max(
            0.0,
            min(100.0, 50.0 + 200.0 * self.realized_roi),
        )

        raw_score = (
            45.0 * self.win_rate
            + 25.0 * early_rate
            + 20.0 * (roi_score / 100.0)
            + 10.0 * confidence
        )

        # Shrink toward zero until sufficient closed trades exist.
        return round(max(0.0, min(100.0, raw_score * confidence)), 2)


class WalletIntelligence:
    """
    In-memory wallet scoring only.

    Important:
    - Solana addresses are case-sensitive: never lowercase them.
    - Pass net realized PnL AFTER fees and execution costs.
    - Call record_closed_trade once per completed position, not per fill.
    - Persisted state and blockchain ingestion are separate components.
    """

    def __init__(self, min_closed_trades: int = 10):
        self.profiles: dict[str, WalletProfile] = {}
        self.token_wallets: dict[str, set[str]] = defaultdict(set)
        self.min_closed_trades = min_closed_trades

    def observe_buy(
        self,
        wallet: str,
        token: str,
        early: bool,
    ) -> None:
        if not wallet or not token:
            raise ValueError("wallet and token are required")

        # Preserve exact Solana base58 addresses.
        profile = self.profiles.setdefault(
            wallet, WalletProfile(address=wallet)
        )

        # Count each wallet/token pair only once.
        if token in profile._seen_tokens:
            return

        profile._seen_tokens.add(token)
        profile.launches_seen += 1

        if early:
            profile.early_entries += 1

        self.token_wallets[token].add(wallet)

    def record_closed_trade(
        self,
        wallet: str,
        trade_id: str,
        net_realized_pnl: float,
        entry_cost: float,
    ) -> None:
        """Record one fully closed position, exactly once per trade_id."""
        if wallet not in self.profiles:
            raise ValueError("Observe the wallet before recording a trade")

        if not trade_id:
            raise ValueError("trade_id is required")

        if trade_id in self.profiles[wallet]._seen_trade_ids:
            return

        if entry_cost <= 0:
            raise ValueError("entry_cost must be positive")

        if net_realized_pnl != net_realized_pnl:
            raise ValueError("PnL must be a finite number")

        if abs(net_realized_pnl) == float("inf"):
            raise ValueError("PnL must be a finite number")

        profile = self.profiles[wallet]
        profile._seen_trade_ids.add(trade_id)
        profile.closed_trades += 1
        profile.realized_pnl += net_realized_pnl
        profile.total_entry_cost += entry_cost

        if net_realized_pnl > 0:
            profile.wins += 1
        elif net_realized_pnl < 0:
            profile.losses += 1
        # Break-even trades count toward closed_trades, not wins/losses.

    def score_wallet(self, wallet: str) -> float:
        profile = self.profiles.get(wallet)
        return profile.score if profile else 0.0

    def score_token(self, token: str) -> float:
        wallets = self.token_wallets.get(token, set())

        # Only score wallets with enough completed-trade history.
        eligible = [
            self.profiles[wallet]
            for wallet in wallets
            if self.profiles[wallet].closed_trades
            >= self.min_closed_trades
        ]

        if not eligible:
            return 0.0

        # Equal weighting avoids one wallet dominating the entire signal.
        return round(
            sum(profile.score for profile in eligible) / len(eligible),
            2,
        )
