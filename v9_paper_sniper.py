
from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Any


@dataclass
class PaperPosition:
    token: str
    entry_price: float
    quantity: float
    entry_ms: int
    score: float
    entry_cost: float


class PaperSniper:
    """Paper simulation only. Never signs or submits transactions."""

    def __init__(
        self,
        starting_cash: float = 35.47,
        position_size: float = 1.0,
        fee_rate: float = 0.01,
        slippage_bps: float = 100.0,
        max_daily_loss_pct: float = 5.0,
        max_open_positions: int = 3,
        storage: Any = None,
    ):
        if not math.isfinite(starting_cash) or starting_cash <= 0:
            raise ValueError("starting_cash must be positive and finite")
        if not math.isfinite(position_size) or position_size <= 0:
            raise ValueError("position_size must be positive and finite")
        if not math.isfinite(fee_rate) or not 0 <= fee_rate < 1:
            raise ValueError("fee_rate must be in [0, 1)")
        if (
            not math.isfinite(slippage_bps)
            or not 0 <= slippage_bps < 10_000
        ):
            raise ValueError("slippage_bps must be in [0, 10000)")
        if (
            not math.isfinite(max_daily_loss_pct)
            or not 0 < max_daily_loss_pct <= 100
        ):
            raise ValueError("Invalid daily loss limit")
        if (
            not isinstance(max_open_positions, int)
            or isinstance(max_open_positions, bool)
            or max_open_positions < 1
        ):
            raise ValueError("max_open_positions must be a positive integer")

        self.starting_cash = float(starting_cash)
        self.cash = float(starting_cash)
        self.position_size = float(position_size)
        self.fee_rate = float(fee_rate)
        self.slippage_bps = float(slippage_bps)
        self.max_daily_loss_pct = float(max_daily_loss_pct)
        self.max_open_positions = max_open_positions
        self.storage = storage

        self.positions: dict[str, PaperPosition] = {}
        self.realized_pnl = 0.0
        self.daily_realized_pnl = 0.0
        self._day = self._utc_day()
        self.closed_trades: list[dict] = []

        # Restore open positions if storage is available.
        # This restores positions, but not the complete account history.
        if self.storage is not None:
            self._restore_open_positions()

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

    def _restore_open_positions(self) -> None:
        rows = self.storage.load_open_positions()

        if len(rows) > self.max_open_positions:
            raise RuntimeError(
                "Stored open positions exceed max_open_positions"
            )

        restored: dict[str, PaperPosition] = {}
        total_cost = 0.0

        for row in rows:
            position = PaperPosition(
                token=str(row["token"]),
                entry_price=float(row["entry_price"]),
                quantity=float(row["quantity"]),
                entry_ms=int(row["entry_time_ms"]),
                score=float(row["score"]),
                entry_cost=float(row["entry_cost"]),
            )

            values = (
                position.entry_price,
                position.quantity,
                position.score,
                position.entry_cost,
            )
            if (
                not position.token
                or any(not math.isfinite(v) for v in values)
                or position.entry_price <= 0
                or position.quantity <= 0
                or position.entry_cost <= 0
                or not 0 <= position.score <= 100
                or position.token in restored
            ):
                raise RuntimeError("Invalid or duplicate stored position")

            restored[position.token] = position
            total_cost += position.entry_cost

        if total_cost > self.cash:
            raise RuntimeError(
                "Stored position costs exceed starting cash. "
                "Account state must be restored before trading."
            )

        self.positions = restored
        self.cash -= total_cost

    def enter(self, token: str, price: float, score: float) -> bool:
        self._roll_day()

        if not isinstance(token, str) or not token.strip():
            return False
        if (
            isinstance(price, bool)
            or not isinstance(price, (int, float))
            or not math.isfinite(price)
            or price <= 0
        ):
            return False
        if (
            isinstance(score, bool)
            or not isinstance(score, (int, float))
            or not math.isfinite(score)
            or not 0 <= score <= 100
        ):
            return False
        if token in self.positions:
            return False
        if len(self.positions) >= self.max_open_positions:
            return False
        if self._daily_loss_limit_hit():
            return False

        fill_price = price * (1 + self.slippage_bps / 10_000)
        size = min(self.position_size, self.cash / (1 + self.fee_rate))
        if size <= 0:
            return False

        fee = size * self.fee_rate
        total_cost = size + fee
        if total_cost > self.cash:
            return False

        position = PaperPosition(
            token=token,
            entry_price=fill_price,
            quantity=size / fill_price,
            entry_ms=int(time.time() * 1000),
            score=float(score),
            entry_cost=total_cost,
        )

        # Persist first; do not change account memory if persistence fails.
        if self.storage is not None:
            self.storage.save_open_position(position)

        self.cash -= total_cost
        self.positions[token] = position
        return True

    def exit(self, token: str, price: float) -> float:
        self._roll_day()

        if (
            isinstance(price, bool)
            or not isinstance(price, (int, float))
            or not math.isfinite(price)
            or price <= 0
        ):
            return 0.0

        position = self.positions.get(token)
        if position is None:
            return 0.0

        fill_price = price * (1 - self.slippage_bps / 10_000)
        gross_proceeds = position.quantity * fill_price
        exit_fee = gross_proceeds * self.fee_rate
        proceeds = gross_proceeds - exit_fee
        pnl = proceeds - position.entry_cost
        exit_ms = int(time.time() * 1000)

        trade = {
            "token": token,
            "entry_ms": position.entry_ms,
            "exit_ms": exit_ms,
            "entry_price": position.entry_price,
            "exit_price": fill_price,
            "quantity": position.quantity,
            "entry_cost": position.entry_cost,
            "proceeds": proceeds,
            "entry_fee": position.entry_cost
            - position.quantity * position.entry_price,
            "exit_fee": exit_fee,
            "pnl": pnl,
            "score": position.score,
        }

        if self.storage is not None:
            # Adapt the simulation result to V9Storage.save_paper_trade.
            from types import SimpleNamespace

            db_trade = SimpleNamespace(
                token=token,
                entry_price=trade["entry_price"],
                exit_price=trade["exit_price"],
                quantity=trade["quantity"],
                pnl_usdt=trade["pnl"],
                entry_cost=trade["entry_cost"],
                proceeds=trade["proceeds"],
                entry_fee=trade["entry_fee"],
                exit_fee=trade["exit_fee"],
                entry_time_ms=trade["entry_ms"],
                exit_time_ms=trade["exit_ms"],
                score=trade["score"],
                reason="paper_exit",
            )

            trade_id = (
                f"{token}:{trade['entry_ms']}:{trade['exit_ms']}"
            )
            saved = self.storage.save_paper_trade(
                db_trade, trade_id=trade_id
            )
            if not saved:
                raise RuntimeError(
                    "Paper trade was not saved; position remains open"
                )

            # Delete only after the closed trade has been saved.
            self.storage.delete_open_position(token)

        self.cash += proceeds
        self.realized_pnl += pnl
        self.daily_realized_pnl += pnl
        self.positions.pop(token)
        self.closed_trades.append(trade)

        return pnl

    def summary(self) -> str:
        return (
            f"PAPER cash={self.cash:.4f} | "
            f"open={len(self.positions)} | "
            f"closed={len(self.closed_trades)} | "
            f"realized_pnl={self.realized_pnl:.4f} | "
            f"daily_pnl={self.daily_realized_pnl:.4f}"
        )
