
import pytest

from v9_wallet_intelligence import WalletIntelligence


def make_wallet(bot, wallet="WalletA", token="TokenA"):
    bot.observe_buy(wallet, token, early=True)


def close_trade(bot, wallet, trade_id, pnl, cost=10.0):
    bot.record_closed_trade(
        wallet=wallet,
        trade_id=trade_id,
        net_realized_pnl=pnl,
        entry_cost=cost,
    )


def test_new_wallet_has_zero_score():
    bot = WalletIntelligence()
    assert bot.score_wallet("unknown") == 0.0


def test_duplicate_buy_counts_only_once():
    bot = WalletIntelligence()

    bot.observe_buy("WalletA", "TokenA", early=True)
    bot.observe_buy("WalletA", "TokenA", early=False)

    profile = bot.profiles["WalletA"]
    assert profile.launches_seen == 1
    assert profile.early_entries == 1


def test_solana_addresses_are_case_sensitive():
    bot = WalletIntelligence()

    bot.observe_buy("AbcWallet", "TokenA", early=True)
    bot.observe_buy("abcWallet", "TokenA", early=True)

    assert "AbcWallet" in bot.profiles
    assert "abcWallet" in bot.profiles
    assert len(bot.profiles) == 2


def test_closed_trade_updates_net_pnl_and_win_count():
    bot = WalletIntelligence()
    make_wallet(bot)

    close_trade(bot, "WalletA", "trade-1", 5.0)
    close_trade(bot, "WalletA", "trade-2", -2.0)

    profile = bot.profiles["WalletA"]
    assert profile.closed_trades == 2
    assert profile.wins == 1
    assert profile.losses == 1
    assert profile.realized_pnl == pytest.approx(3.0)
    assert profile.total_entry_cost == pytest.approx(20.0)


def test_duplicate_trade_id_is_ignored():
    bot = WalletIntelligence()
    make_wallet(bot)

    close_trade(bot, "WalletA", "trade-1", 5.0)
    close_trade(bot, "WalletA", "trade-1", 5.0)

    profile = bot.profiles["WalletA"]
    assert profile.closed_trades == 1
    assert profile.realized_pnl == pytest.approx(5.0)


def test_invalid_trade_data_is_rejected():
    bot = WalletIntelligence()
    make_wallet(bot)

    with pytest.raises(ValueError):
        close_trade(bot, "WalletA", "bad-cost", 1.0, cost=0)

    with pytest.raises(ValueError):
        close_trade(bot, "WalletA", "bad-pnl", float("nan"))

    with pytest.raises(ValueError):
        close_trade(bot, "WalletA", "infinite-pnl", float("inf"))


def test_unknown_wallet_cannot_record_trade():
    bot = WalletIntelligence()

    with pytest.raises(ValueError):
        close_trade(bot, "Unknown", "trade-1", 1.0)


def test_profitable_wallet_scores_higher_than_losing_wallet():
    bot = WalletIntelligence()

    make_wallet(bot, "Winner", "TokenA")
    make_wallet(bot, "Loser", "TokenB")

    for i in range(10):
        close_trade(bot, "Winner", f"win-{i}", 2.0)
        close_trade(bot, "Loser", f"loss-{i}", -2.0)

    assert bot.score_wallet("Winner") > bot.score_wallet("Loser")


def test_token_score_requires_enough_closed_trades():
    bot = WalletIntelligence(min_closed_trades=10)
    make_wallet(bot, "WalletA", "TokenA")

    # Nine completed trades are insufficient.
    for i in range(9):
        close_trade(bot, "WalletA", f"trade-{i}", 2.0)

    assert bot.score_token("TokenA") == 0.0

    # The tenth completed trade makes the wallet eligible.
    close_trade(bot, "WalletA", "trade-9", 2.0)
    assert bot.score_token("TokenA") > 0.0


def test_break_even_trade_counts_as_closed():
    bot = WalletIntelligence()
    make_wallet(bot)

    close_trade(bot, "WalletA", "trade-1", 0.0)

    profile = bot.profiles["WalletA"]
    assert profile.closed_trades == 1
    assert profile.wins == 0
    assert profile.losses == 0


def test_empty_token_has_zero_score():
    bot = WalletIntelligence()
    assert bot.score_token("UnknownToken") == 0.0
