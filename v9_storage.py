
from __future__ import annotations

import json
import math
import sqlite3
import time
from pathlib import Path
from typing import Any

DB_PATH = Path("v9_data.sqlite3")


class V9Storage:
    """SQLite storage for V9 metadata and paper-only trade records."""

    def __init__(self, path: Path | str = DB_PATH):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(self.path, timeout=10.0)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")

        self._init()

    def _init(self) -> None:
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS tokens (
            address TEXT PRIMARY KEY,
            block_number INTEGER,
            tx_hash TEXT,
            deployer TEXT,
            name TEXT,
            symbol TEXT,
            decimals INTEGER,
            total_supply TEXT,
            created_at_ms INTEGER,
            liquidity_usdt REAL,
            top_holder_share_pct REAL,
            dev_share_pct REAL,
            total_score REAL,
            decision TEXT,
            reasons_json TEXT
        );

        CREATE TABLE IF NOT EXISTS wallet_profiles (
            address TEXT PRIMARY KEY,
            first_seen_ms INTEGER,
            launches_seen INTEGER NOT NULL DEFAULT 0,
            early_entries INTEGER NOT NULL DEFAULT 0,
            wins INTEGER NOT NULL DEFAULT 0,
            losses INTEGER NOT NULL DEFAULT 0,
            realized_pnl REAL NOT NULL DEFAULT 0,
            total_entry_cost REAL NOT NULL DEFAULT 0,
            closed_trades INTEGER NOT NULL DEFAULT 0,
            score REAL NOT NULL DEFAULT 0,
            seen_tokens_json TEXT NOT NULL DEFAULT '[]',
            seen_trade_ids_json TEXT NOT NULL DEFAULT '[]'
        );

        CREATE TABLE IF NOT EXISTS wallet_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wallet TEXT NOT NULL,
            token TEXT NOT NULL,
            event_type TEXT NOT NULL,
            block_number INTEGER,
            tx_hash TEXT,
            amount TEXT,
            timestamp_ms INTEGER,
            event_key TEXT UNIQUE
        );

        CREATE TABLE IF NOT EXISTS paper_positions (
            token TEXT PRIMARY KEY,
            entry_price REAL NOT NULL,
            quantity REAL NOT NULL,
            entry_time_ms INTEGER NOT NULL,
            score REAL NOT NULL,
            entry_cost REAL NOT NULL,
            updated_at_ms INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS paper_trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_id TEXT UNIQUE,
            token TEXT NOT NULL,
            entry_price REAL NOT NULL,
            exit_price REAL NOT NULL,
            quantity REAL NOT NULL,
            pnl_usdt REAL NOT NULL,
            entry_cost REAL,
            proceeds REAL,
            entry_fee REAL,
            exit_fee REAL,
            entry_time_ms INTEGER NOT NULL,
            exit_time_ms INTEGER NOT NULL,
            score REAL NOT NULL,
            reason TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS wallet_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            state_json TEXT NOT NULL,
            updated_at_ms INTEGER NOT NULL
        );
        """)

        self._migrate_legacy_columns()
        self.conn.commit()

    def _migrate_legacy_columns(self) -> None:
        migrations = {
            "wallet_profiles": {
                "total_entry_cost": "REAL NOT NULL DEFAULT 0",
                "closed_trades": "INTEGER NOT NULL DEFAULT 0",
                "seen_tokens_json": "TEXT NOT NULL DEFAULT '[]'",
                "seen_trade_ids_json": "TEXT NOT NULL DEFAULT '[]'",
            },
            "wallet_events": {
                "event_key": "TEXT",
            },
            "paper_trades": {
                "trade_id": "TEXT",
                "entry_cost": "REAL",
                "proceeds": "REAL",
                "entry_fee": "REAL",
                "exit_fee": "REAL",
            },
        }

        for table, columns in migrations.items():
            existing = {
                row["name"]
                for row in self.conn.execute(
                    f"PRAGMA table_info({table})"
                ).fetchall()
            }

            for column, sql_type in columns.items():
                if column not in existing:
                    self.conn.execute(
                        f"ALTER TABLE {table} ADD COLUMN {column} {sql_type}"
                    )

        self.conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_wallet_events_event_key
            ON wallet_events(event_key)
            WHERE event_key IS NOT NULL
        """)

        self.conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_paper_trades_trade_id
            ON paper_trades(trade_id)
            WHERE trade_id IS NOT NULL
        """)

    def save_token(self, token: Any) -> None:
        self.conn.execute("""
        INSERT INTO tokens (
            address, block_number, tx_hash, deployer, name, symbol,
            decimals, total_supply, created_at_ms, liquidity_usdt,
            top_holder_share_pct, dev_share_pct, total_score,
            decision, reasons_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(address) DO UPDATE SET
            block_number=excluded.block_number,
            tx_hash=excluded.tx_hash,
            deployer=excluded.deployer,
            name=excluded.name,
            symbol=excluded.symbol,
            decimals=excluded.decimals,
            total_supply=excluded.total_supply,
            created_at_ms=excluded.created_at_ms,
            liquidity_usdt=excluded.liquidity_usdt,
            top_holder_share_pct=excluded.top_holder_share_pct,
            dev_share_pct=excluded.dev_share_pct,
            total_score=excluded.total_score,
            decision=excluded.decision,
            reasons_json=excluded.reasons_json
        """, (
            token.address,
            token.block_number,
            token.tx_hash,
            token.deployer,
            token.name,
            token.symbol,
            token.decimals,
            str(token.total_supply)
            if token.total_supply is not None else None,
            token.created_at_ms,
            token.liquidity_usdt,
            token.top_holder_share_pct,
            token.dev_share_pct,
            token.total_score,
            token.decision,
            json.dumps(token.reasons),
        ))
        self.conn.commit()

    def save_wallet_event(
        self,
        wallet: str,
        token: str,
        event_type: str,
        block: int | None,
        tx_hash: str | None,
        amount: Any,
        ts: int | None,
        event_key: str | None = None,
    ) -> bool:
        if not wallet or not token or not event_type:
            raise ValueError(
                "wallet, token and event_type are required"
            )

        if event_key is None and tx_hash:
            event_key = f"{tx_hash}:{wallet}:{token}:{event_type}"

        cur = self.conn.execute("""
            INSERT OR IGNORE INTO wallet_events (
                wallet, token, event_type, block_number,
                tx_hash, amount, timestamp_ms, event_key
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            wallet, token, event_type, block, tx_hash,
            str(amount), ts, event_key,
        ))

        self.conn.commit()
        return cur.rowcount == 1

    def save_wallet_intelligence(
        self,
        bot: Any,
        updated_at_ms: int | None = None,
    ) -> None:
        """Persist a complete wallet-intelligence snapshot."""
        state = bot.export_state()

        if updated_at_ms is None:
            updated_at_ms = int(time.time() * 1000)

        state_json = json.dumps(state, allow_nan=False)

        with self.conn:
            for profile in state["profiles"]:
                address = profile["address"]

                self.conn.execute("""
                INSERT INTO wallet_profiles (
                    address, launches_seen, early_entries, wins, losses,
                    realized_pnl, total_entry_cost, closed_trades, score,
                    seen_tokens_json, seen_trade_ids_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(address) DO UPDATE SET
                    launches_seen=excluded.launches_seen,
                    early_entries=excluded.early_entries,
                    wins=excluded.wins,
                    losses=excluded.losses,
                    realized_pnl=excluded.realized_pnl,
                    total_entry_cost=excluded.total_entry_cost,
                    closed_trades=excluded.closed_trades,
                    score=excluded.score,
                    seen_tokens_json=excluded.seen_tokens_json,
                    seen_trade_ids_json=excluded.seen_trade_ids_json
                """, (
                    address,
                    profile["launches_seen"],
                    profile["early_entries"],
                    profile["wins"],
                    profile["losses"],
                    profile["realized_pnl"],
                    profile["total_entry_cost"],
                    profile["closed_trades"],
                    bot.score_wallet(address),
                    json.dumps(profile["seen_tokens"]),
                    json.dumps(profile["seen_trade_ids"]),
                ))

            self.conn.execute("""
                INSERT INTO wallet_state(id, state_json, updated_at_ms)
                VALUES (1, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    state_json=excluded.state_json,
                    updated_at_ms=excluded.updated_at_ms
            """, (state_json, updated_at_ms))

    def load_wallet_intelligence(self):
        from v9_wallet_intelligence import WalletIntelligence

        row = self.conn.execute(
            "SELECT state_json FROM wallet_state WHERE id=1"
        ).fetchone()

        if row:
            return WalletIntelligence.from_state(
                json.loads(row["state_json"])
            )

        # Fallback for older databases without a full snapshot.
        rows = self.conn.execute(
            "SELECT * FROM wallet_profiles"
        ).fetchall()

        if not rows:
            return WalletIntelligence()

        profiles = []
        for row in rows:
            profiles.append({
                "address": row["address"],
                "launches_seen": row["launches_seen"],
                "early_entries": row["early_entries"],
                "wins": row["wins"],
                "losses": row["losses"],
                "realized_pnl": row["realized_pnl"],
                "total_entry_cost": row["total_entry_cost"],
                "closed_trades": row["closed_trades"],
                "seen_tokens": json.loads(
                    row["seen_tokens_json"] or "[]"
                ),
                "seen_trade_ids": json.loads(
                    row["seen_trade_ids_json"] or "[]"
                ),
            })

        return WalletIntelligence.from_state({
            "min_closed_trades": 10,
            "profiles": profiles,
        })

    def save_open_position(self, position: Any) -> None:
        now_ms = int(time.time() * 1000)

        entry_time_ms = getattr(
            position,
            "entry_ms",
            getattr(position, "entry_time_ms", now_ms),
        )
        entry_cost = getattr(
            position,
            "entry_cost",
            position.quantity * position.entry_price,
        )

        values = (
            position.entry_price,
            position.quantity,
            position.score,
            entry_cost,
        )

        if any(
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(float(value))
            for value in values
        ):
            raise ValueError("Position values must be finite numbers")

        if (
            position.entry_price <= 0
            or position.quantity <= 0
            or entry_cost <= 0
        ):
            raise ValueError("Position prices, quantity and cost must be positive")

        self.conn.execute("""
        INSERT INTO paper_positions (
            token, entry_price, quantity, entry_time_ms,
            score, entry_cost, updated_at_ms
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(token) DO UPDATE SET
            entry_price=excluded.entry_price,
            quantity=excluded.quantity,
            entry_time_ms=excluded.entry_time_ms,
            score=excluded.score,
            entry_cost=excluded.entry_cost,
            updated_at_ms=excluded.updated_at_ms
        """, (
            position.token, position.entry_price, position.quantity,
            entry_time_ms, position.score, entry_cost, now_ms,
        ))

        self.conn.commit()

    def delete_open_position(self, token: str) -> None:
        self.conn.execute(
            "DELETE FROM paper_positions WHERE token=?",
            (token,),
        )
        self.conn.commit()

    def load_open_positions(self) -> list[dict]:
        rows = self.conn.execute("""
            SELECT * FROM paper_positions
            ORDER BY entry_time_ms
        """).fetchall()

        return [dict(row) for row in rows]

    def save_paper_trade(
        self,
        trade: Any,
        trade_id: str | None = None,
    ) -> bool:
        """Save a completed paper trade once per stable trade ID."""
        if trade_id is None:
            trade_id = getattr(trade, "trade_id", None)

        if not trade_id:
            trade_id = (
                f"{trade.token}:{trade.entry_time_ms}:"
                f"{trade.exit_time_ms}:{trade.quantity}:{trade.pnl_usdt}"
            )

        values = {
            "entry_price": float(trade.entry_price),
            "exit_price": float(trade.exit_price),
            "quantity": float(trade.quantity),
            "pnl_usdt": float(trade.pnl_usdt),
            "score": float(trade.score),
        }

        for name, value in values.items():
            if not math.isfinite(value):
                raise ValueError(f"{name} must be finite")

        if (
            values["entry_price"] <= 0
            or values["exit_price"] <= 0
            or values["quantity"] <= 0
        ):
            raise ValueError("Prices and quantity must be positive")

        cur = self.conn.execute("""
        INSERT OR IGNORE INTO paper_trades (
            trade_id, token, entry_price, exit_price, quantity,
            pnl_usdt, entry_cost, proceeds, entry_fee, exit_fee,
            entry_time_ms, exit_time_ms, score, reason
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            trade_id,
            trade.token,
            values["entry_price"],
            values["exit_price"],
            values["quantity"],
            values["pnl_usdt"],
            getattr(trade, "entry_cost", None),
            getattr(trade, "proceeds", None),
            getattr(trade, "entry_fee", None),
            getattr(trade, "exit_fee", None),
            int(trade.entry_time_ms),
            int(trade.exit_time_ms),
            values["score"],
            str(getattr(
                trade,
                "decision_reason",
                getattr(trade, "reason", ""),
            )),
        ))

        self.conn.commit()
        return cur.rowcount == 1

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "V9Storage":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
