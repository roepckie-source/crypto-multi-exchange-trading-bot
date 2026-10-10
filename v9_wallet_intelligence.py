
from __future__ import annotations

import math
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
        if self.launches_seen <= 0:
            return 0.0

        confidence = min(1.0, self.closed_trades / 20.0)
        early_rate = self.early_entries / self.launches_seen

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

        return round(max(0.0, min(100.0, raw_score * confidence)), 2)


class WalletIntelligence:
    """In-memory wallet scoring. Use V9Storage for persistence."""

    def __init__(self, min_closed_trades: int = 10):
        if (
            not isinstance(min_closed_trades, int)
            or isinstance(min_closed_trades, bool)
            or min_closed_trades < 1
        ):
            raise ValueError("min_closed_trades must be a positive integer")

        self.profiles: dict[str, WalletProfile] = {}
        self.token_wallets: dict[str, set[str]] = defaultdict(set)
        self.min_closed_trades = min_closed_trades

    def observe_buy(self, wallet: str, token: str, early: bool) -> bool:
        if not isinstance(wallet, str) or not wallet.strip():
            raise ValueError("wallet is required")
        if not isinstance(token, str) or not token.strip():
            raise ValueError("token is required")
        if not isinstance(early, bool):
            raise ValueError("early must be a bool")

        profile = self.profiles.setdefault(
            wallet, WalletProfile(address=wallet)
        )

        if token in profile._seen_tokens:
            return False

        profile._seen_tokens.add(token)
        profile.launches_seen += 1

        if early:
            profile.early_entries += 1

        self.token_wallets[token].add(wallet)
        return True

    def record_closed_trade(
        self,
        wallet: str,
        trade_id: str,
        net_realized_pnl: float,
        entry_cost: float,
    ) -> bool:
        """Record a fully closed position once per stable trade ID."""
        if not isinstance(wallet, str) or wallet not in self.profiles:
            raise ValueError(
                "Observe or restore the wallet before recording a trade"
            )

        if not isinstance(trade_id, str) or not trade_id.strip():
            raise ValueError("trade_id is required")

        if (
            isinstance(net_realized_pnl, bool)
            or not isinstance(net_realized_pnl, (int, float))
            or not math.isfinite(float(net_realized_pnl))
        ):
            raise ValueError("PnL must be a finite number")

        if (
            isinstance(entry_cost, bool)
            or not isinstance(entry_cost, (int, float))
            or not math.isfinite(float(entry_cost))
            or entry_cost <= 0
        ):
            raise ValueError("entry_cost must be a finite positive number")

        profile = self.profiles[wallet]

        if trade_id in profile._seen_trade_ids:
            return False

        pnl = float(net_realized_pnl)
        cost = float(entry_cost)

        profile._seen_trade_ids.add(trade_id)
        profile.closed_trades += 1
        profile.realized_pnl += pnl
        profile.total_entry_cost += cost

        if pnl > 0:
            profile.wins += 1
        elif pnl < 0:
            profile.losses += 1

        return True

    def score_wallet(self, wallet: str) -> float:
        profile = self.profiles.get(wallet)
        return profile.score if profile else 0.0

    def score_token(self, token: str) -> float:
        wallets = self.token_wallets.get(token, set())

        eligible = [
            self.profiles[wallet]
            for wallet in wallets
            if self.profiles[wallet].closed_trades
            >= self.min_closed_trades
        ]

        if not eligible:
            return 0.0

        return round(
            sum(profile.score for profile in eligible) / len(eligible),
            2,
        )

    def export_state(self) -> dict:
        """Return a JSON-serializable snapshot."""
        return {
            "min_closed_trades": self.min_closed_trades,
            "profiles": [
                {
                    "address": profile.address,
                    "launches_seen": profile.launches_seen,
                    "early_entries": profile.early_entries,
                    "wins": profile.wins,
                    "losses": profile.losses,
                    "realized_pnl": profile.realized_pnl,
                    "total_entry_cost": profile.total_entry_cost,
                    "closed_trades": profile.closed_trades,
                    "seen_tokens": sorted(profile._seen_tokens),
                    "seen_trade_ids": sorted(profile._seen_trade_ids),
                }
                for profile in sorted(
                    self.profiles.values(),
                    key=lambda item: item.address,
                )
            ],
        }

    @classmethod
    def from_state(cls, state: dict) -> "WalletIntelligence":
        if not isinstance(state, dict):
            raise ValueError("Invalid wallet intelligence state")

        profiles_data = state.get("profiles", [])
        if not isinstance(profiles_data, list):
            raise ValueError("Invalid profiles in wallet state")

        bot = cls(
            min_closed_trades=state.get("min_closed_trades", 10)
        )

        for item in profiles_data:
            if not isinstance(item, dict):
                raise ValueError("Invalid wallet profile in state")

            address = item.get("address")
            if not isinstance(address, str) or not address:
                raise ValueError("Invalid wallet address in state")
            if address in bot.profiles:
                raise ValueError("Duplicate wallet in state")

            profile = WalletProfile(
                address=address,
                launches_seen=int(item.get("launches_seen", 0)),
                early_entries=int(item.get("early_entries", 0)),
                wins=int(item.get("wins", 0)),
                losses=int(item.get("losses", 0)),
                realized_pnl=float(item.get("realized_pnl", 0.0)),
                total_entry_cost=float(item.get("total_entry_cost", 0.0)),
                closed_trades=int(item.get("closed_trades", 0)),
            )

            profile._seen_tokens = set(item.get("seen_tokens", []))
            profile._seen_trade_ids = set(item.get("seen_trade_ids", []))

            if any(
                not math.isfinite(value)
                for value in (
                    profile.realized_pnl,
                    profile.total_entry_cost,
                )
            ):
                raise ValueError("Non-finite values in wallet state")

            counters = (
                profile.launches_seen,
                profile.early_entries,
                profile.wins,
                profile.losses,
                profile.closed_trades,
            )
            if min(counters) < 0:
                raise ValueError("Negative counters in wallet state")

            if profile.early_entries > profile.launches_seen:
                raise ValueError("Inconsistent early-entry counter")

            if profile.wins + profile.losses > profile.closed_trades:
                raise ValueError("Inconsistent closed-trade counters")

            if profile.total_entry_cost < 0:
                raise ValueError("Negative total entry cost")

            if len(profile._seen_tokens) > profile.launches_seen:
                raise ValueError("Inconsistent seen-token state")

            if len(profile._seen_trade_ids) > profile.closed_trades:
                raise ValueError("Inconsistent seen-trade state")

            bot.profiles[address] = profile

            for token in profile._seen_tokens:
                bot.token_wallets[token].add(address)

        return bot
