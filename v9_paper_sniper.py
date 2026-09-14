from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class PaperPosition:
    token: str
    entry_price: float
    quantity: float
    entry_ms: int
    score: float


class PaperSniper:
    def __init__(self, starting_cash: float = 35.47, position_size: float = 1.0):
        self.cash = starting_cash
        self.position_size = position_size
        self.positions: dict[str, PaperPosition] = {}
        self.realized_pnl = 0.0

    def enter(self, token: str, price: float, score: float) -> bool:
        if token in self.positions or price <= 0:
            return False

        size = min(self.position_size, self.cash)
        if size <= 0:
            return False

        qty = size / price
        self.cash -= size
        self.positions[token] = PaperPosition(
            token, price, qty, int(time.time() * 1000), score
        )
        return True

    def exit(self, token: str, price: float) -> float:
        position = self.positions.pop(token, None)
        if not position or price <= 0:
            return 0.0

        proceeds = position.quantity * price
        cost = position.quantity * position.entry_price
        pnl = proceeds - cost
        self.cash += proceeds
        self.realized_pnl += pnl
        return pnl

    def summary(self) -> str:
        return (
            f"PAPER cash={self.cash:.4f} | "
            f"open={len(self.positions)} | "
            f"realized_pnl={self.realized_pnl:.4f}"
        )
