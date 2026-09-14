import json
import sqlite3
from pathlib import Path
from typing import Iterable

DB_PATH = Path("v9_data.sqlite3")


class V9Storage:
    def __init__(self, path: Path = DB_PATH):
        self.conn = sqlite3.connect(path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._init()

    def _init(self):
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
            launches_seen INTEGER DEFAULT 0,
            early_entries INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            realized_pnl REAL DEFAULT 0,
            score REAL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS wallet_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wallet TEXT,
            token TEXT,
            event_type TEXT,
            block_number INTEGER,
            tx_hash TEXT,
            amount TEXT,
            timestamp_ms INTEGER
        );

        CREATE TABLE IF NOT EXISTS paper_trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT,
            entry_price REAL,
            exit_price REAL,
            quantity REAL,
            pnl_usdt REAL,
            entry_time_ms INTEGER,
            exit_time_ms INTEGER,
            score REAL,
            reason TEXT
        );
        """)
        self.conn.commit()

    def save_token(self, token):
        self.conn.execute("""
        INSERT OR REPLACE INTO tokens
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            token.address, token.block_number, token.tx_hash,
            token.deployer, token.name, token.symbol, token.decimals,
            str(token.total_supply) if token.total_supply is not None else None,
            token.created_at_ms, token.liquidity_usdt,
            token.top_holder_share_pct, token.dev_share_pct,
            token.total_score, token.decision, json.dumps(token.reasons),
        ))
        self.conn.commit()

    def save_wallet_event(self, wallet, token, event_type, block, tx_hash, amount, ts):
        self.conn.execute("""
        INSERT INTO wallet_events
        (wallet, token, event_type, block_number, tx_hash, amount, timestamp_ms)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (wallet, token, event_type, block, tx_hash, str(amount), ts))
        self.conn.commit()

    def save_paper_trade(self, trade):
        self.conn.execute("""
        INSERT INTO paper_trades
        (token, entry_price, exit_price, quantity, pnl_usdt,
         entry_time_ms, exit_time_ms, score, reason)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            trade.token, trade.entry_price, trade.exit_price,
            trade.quantity, trade.pnl_usdt, trade.entry_time_ms,
            trade.exit_time_ms, trade.score, trade.decision_reason,
        ))
        self.conn.commit()
