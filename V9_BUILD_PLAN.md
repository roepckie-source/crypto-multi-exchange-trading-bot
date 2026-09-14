# V9 build plan

## Gate 0 — chain connectivity
PASS when blocks can be read reliably.

## Gate 1 — launch discovery
Detect newly created ERC-20 contracts and persist them.

## Gate 2 — DEX discovery
Configure only verified factory/router/pool addresses.

## Gate 3 — executable paper pricing
Get a real DEX quote for each candidate.

## Gate 4 — risk engine
Hard veto:
- mint risk
- blacklist risk
- pause risk
- excessive holder concentration
- unsafe liquidity
- suspicious tax
- suspicious deployer history

## Gate 5 — wallet intelligence
Track historical wallet behaviour and build reproducible scores.

## Gate 6 — replay
Replay historical blocks and measure:
- detection latency
- false positives
- paper entry quality
- max drawdown
- expectancy
- win rate
- profit factor

## Gate 7 — paper live
Run continuously with zero signing capability.

## Gate 8 — only after evidence
Consider a separately isolated execution service.
