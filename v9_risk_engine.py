from __future__ import annotations

from v9_models import TokenCandidate


def evaluate(token: TokenCandidate) -> TokenCandidate:
    # Hard vetoes first.
    hard_fail = False

    if token.mint_authority_risk:
        token.reasons.append("MINT_RISK")
        hard_fail = True

    if token.blacklist_risk:
        token.reasons.append("BLACKLIST_RISK")
        hard_fail = True

    if token.pause_risk:
        token.reasons.append("PAUSE_RISK")
        hard_fail = True

    if token.tax_risk:
        token.reasons.append("TAX_RISK")
        hard_fail = True

    if token.liquidity_risk:
        token.reasons.append("LIQUIDITY_RISK")
        hard_fail = True

    if hard_fail:
        token.decision = "SKIP"
        token.total_score = 0.0
        return token

    token.contract_score = max(0.0, min(100.0, token.contract_score))
    token.liquidity_score = max(0.0, min(100.0, token.liquidity_score))
    token.wallet_score = max(0.0, min(100.0, token.wallet_score))

    token.total_score = (
        token.contract_score * 0.40
        + token.liquidity_score * 0.25
        + token.wallet_score * 0.35
    )

    if token.total_score >= 80:
        token.decision = "PAPER_BUY"
    elif token.total_score >= 65:
        token.decision = "WATCH"
    else:
        token.decision = "SKIP"

    return token
