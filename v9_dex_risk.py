def apply_market_risk(token,liquidity_usdt,top_holder_share_pct,min_liquidity_usdt,max_top_holder_share_pct):
    token.liquidity_usdt=liquidity_usdt
    token.top_holder_share_pct=top_holder_share_pct
    if liquidity_usdt is None:
        token.liquidity_risk=True; token.reasons.append("LIQUIDITY_UNKNOWN")
    elif liquidity_usdt<min_liquidity_usdt:
        token.liquidity_risk=True; token.reasons.append("LIQUIDITY_TOO_LOW")
    if top_holder_share_pct is not None and top_holder_share_pct>max_top_holder_share_pct:
        token.liquidity_risk=True; token.reasons.append("TOP_HOLDER_CONCENTRATION")
    token.liquidity_score=0 if liquidity_usdt is None or liquidity_usdt<min_liquidity_usdt else min(100,40+60*min(1,liquidity_usdt/100000))
    return token
