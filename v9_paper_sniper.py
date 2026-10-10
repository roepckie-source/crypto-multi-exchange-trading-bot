
from __future__ import annotations

import math
import time
from dataclasses import dataclass


@dataclass
class PaperPosition:
    token: str
    entry_price: float
    quantity: float
    entry_ms: int
    score: float
    entry_cost: float


class PaperSniper:
    """Simulation only. Never signs or submits blockchain transactions."""

    def __init__(
        self,
        starting_cash: float = 35.47,
        position_size: float = 1.0,
        fee_rate: float = 0.01,
        slippage_bps: float = 100.0,
        max_daily_loss_pct: float = 5.0,
        max_open_positions: int = 3,
    ):
        if starting_cash <= 0 or position_size <= 0:
            raise ValueError("Cash and position size must be positive")
        if not 0 <= fee_rate < 1:
            raise ValueError("fee_rate must be in [0, 1)")
        if not 0 <= slippage_bps < 10_000:
            raise ValueError("slippage_bps must be in [0, 10000)")
        if not 0 < max_daily_loss_pct <= 100:
            raise ValueError("Invalid daily loss limit")
        if max_open_positions < 1:
            raise ValueError("max_open_positions must be positive")

        self.cash = float(starting_cash)
        self.starting_cash = float(starting_cash)
        self.position_size = float(position_size)
        self.fee_rate = fee_rate
        self.slippage_bps = slippage_bps
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_open_positions = max_open_positions

        self.positions: dict[str, PaperPosition] = {}
        self.realized_pnl = 0.0
        self.daily_realized_pnl = 0.0
        self._day = self._utc_day()
        self.closed_trades: list[dict] = []

    @staticmethod
    def _utc_day() -> str:
        return time.strftime("%Y-%m-%d", time.gmtime())

    def _roll_day(self) -> None:
        today = self._utc_day()
        if today != self._day:
            self._day = today
            self.daily_realized_pnl = 0.0

    def _daily_loss_limit_hit(self) -> bool:
        limit = self.starting_cash * self.max_daily_loss_pct / 100
        return self.daily_realized_pnl <= -limit

    def enter(self, token: str, price: float, score: float) -> bool:
        self._roll_day()

        if not token or not math.isfinite(price) or price <= 0:
            return False
        if not math.isfinite(score) or not 0 <= score <= 100:
            return False
        if token in self.positions:
            return False
        if len(self.positions) >= self.max_open_positions:
            return False
        if self._daily_loss_limit_hit():
            return False

        # Simulate paying a worse price on entry.
        fill_price = price * (1 + self.slippage_bps / 10_000)
        size = min(self.position_size, self.cash / (1 + self.fee_rate))
        if size <= 0:
            return False

        fee = size * self.fee_rate
        total_cost = size + fee
        if total_cost > self.cash:
            return False

        qty = size / fill_price
        self.cash -= total_cost

        self.positions[token] = PaperPosition(
            token=token,
            entry_price=fill_price,
            quantity=qty,
            entry_ms=int(time.time() * 1000),
            score=score,
            entry_cost=total_cost,
        )
        return True

    def exit(self, token: str, price: float) -> float:
        self._roll_day()

        # Validate BEFORE removing the open position.
        if not math.isfinite(price) or price <= 0:
            return 0.0

        position = self.positions.get(token)
        if position is None:
            return 0.0

        # Simulate a worse sale price and deduct exit fee.
        fill_price = price * (1 - self.slippage_bps / 10_000)
        gross_proceeds = position.quantity * fill_price
        exit_fee = gross_proceeds * self.fee_rate
        proceeds = gross_proceeds - exit_fee
        pnl = proceeds - position.entry_cost

        self.cash += proceeds
        self.realized_pnl += pnl
        self.daily_realized_pnl += pnl
        self.positions.pop(token)

        self.closed_trades.append({
            "token": token,
            "entry_ms": position.entry_ms,
            "exit_ms": int(time.time() * 1000),
            "entry_price": position.entry_price,
            "exit_price": fill_price,
            "quantity": position.quantity,
            "entry_cost": position.entry_cost,
            "proceeds": proceeds,
            "pnl": pnl,
            "score": position.score,
        })

        return pnl

    def summary(self) -> str:
        return (
            f"PAPER cash={self.cash:.4f} | "
            f"open={len(self.positions)} | "
            f"closed={len(self.closed_trades)} | "
            f"realized_pnl={self.realized_pnl:.4f} | "
            f"daily_pnl={self.daily_realized_pnl:.4f}"
        )
