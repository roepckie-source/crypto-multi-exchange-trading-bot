from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass


@dataclass
class WalletProfile:
    address: str
    launches_seen: int = 0
    early_entries: int = 0
    wins: int = 0
    losses: int = 0
    realized_pnl: float = 0.0

    @property
    def score(self) -> float:
        if self.launches_seen <= 0:
            return 0.0

        win_rate = self.wins / max(1, self.wins + self.losses)
        early_rate = self.early_entries / max(1, self.launches_seen)

        score = (
            45.0 * win_rate
            + 35.0 * early_rate
            + 20.0 * min(1.0, max(0.0, self.realized_pnl / 1000.0))
        )
        return max(0.0, min(100.0, score))


class WalletIntelligence:
    def __init__(self):
        self.profiles: dict[str, WalletProfile] = {}
        self.token_wallets: dict[str, set[str]] = defaultdict(set)

    def observe_buy(self, wallet: str, token: str, early: bool):
        wallet = wallet.lower()
        profile = self.profiles.setdefault(wallet, WalletProfile(wallet))
        profile.launches_seen += 1
        if early:
            profile.early_entries += 1
        self.token_wallets[token.lower()].add(wallet)

    def score_token(self, token: str) -> float:
        wallets = self.token_wallets.get(token.lower(), set())
        if not wallets:
            return 0.0

        scores = sorted(
            (self.profiles[w].score for w in wallets if w in self.profiles),
            reverse=True,
        )
        if not scores:
            return 0.0

        # Reward several independent strong wallets, but cap the influence.
        top = scores[:10]
        return min(100.0, sum(top) / len(top) + min(20.0, len(top) * 2.0))
