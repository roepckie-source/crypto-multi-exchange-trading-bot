
import json

import pytest

from v9_storage import V9Storage
from v9_wallet_intelligence import WalletIntelligence


def test_wallet_intelligence_survives_database_restart(tmp_path):
    db_path = tmp_path / "test_v9.sqlite3"

    bot = WalletIntelligence(min_closed_trades=1)
    bot.observe_buy("wallet-A", "token-X", early=True)

    for i in range(3):
        bot.record_closed_trade(
            wallet="wallet-A",
            trade_id=f"trade-{i}",
            net_realized_pnl=2.0,
            entry_cost=10.0,
        )

    with V9Storage(db_path) as storage:
        storage.save_wallet_intelligence(bot)

    # Reopen the database as if the application had restarted.
    with V9Storage(db_path) as storage:
        restored = storage.load_wallet_intelligence()

    assert restored.score_wallet("wallet-A") == bot.score_wallet("wallet-A")
    assert restored.profiles["wallet-A"].closed_trades == 3
    assert restored.profiles["wallet-A"].realized_pnl == pytest.approx(6.0)
    assert restored.score_token("token-X") == bot.score_token("token-X")


def test_wallet_snapshot_rejects_non_finite_values():
    bad_state = {
        "min_closed_trades": 1,
        "profiles": [
            {
                "address": "wallet-A",
                "launches_seen": 1,
                "early_entries": 1,
                "wins": 0,
                "losses": 0,
                "realized_pnl": float("nan"),
                "total_entry_cost": 0.0,
                "closed_trades": 0,
                "seen_tokens": ["token-X"],
                "seen_trade_ids": [],
            }
        ],
    }

    with pytest.raises(ValueError):
        WalletIntelligence.from_state(bad_state)


def test_duplicate_wallet_event_is_ignored(tmp_path):
    db_path = tmp_path / "events.sqlite3"

    with V9Storage(db_path) as storage:
        first = storage.save_wallet_event(
            wallet="wallet-A",
            token="token-X",
            event_type="BUY",
            block=123,
            tx_hash="0xabc",
            amount="10",
            ts=1_800_000_000_000,
        )

        duplicate = storage.save_wallet_event(
            wallet="wallet-A",
            token="token-X",
            event_type="BUY",
            block=123,
            tx_hash="0xabc",
            amount="10",
            ts=1_800_000_000_000,
        )

    assert first is True
    assert duplicate is False
