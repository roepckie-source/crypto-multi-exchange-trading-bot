# V9 Meme Sniper / On-Chain Intelligence

V9 is a PAPER-ONLY research engine inspired by the on-chain meme-sniper
architecture discussed in the reference posts.

## Target chain

Robinhood Chain mainnet:
- Chain ID: 4663
- Public RPC: https://rpc.mainnet.chain.robinhood.com

Robinhood Chain is EVM-compatible. The public RPC is rate-limited, so a
WebSocket/data provider should be used for serious real-time monitoring.

## What V9.0 currently does

1. Connects to Robinhood Chain.
2. Walks new blocks.
3. Finds contract-creation transactions.
4. Tests created contracts for ERC-20 metadata.
5. Runs conservative contract bytecode heuristics.
6. Stores token candidates in SQLite.
7. Calculates a risk score.
8. Has a persistent wallet-intelligence database.
9. Has a paper-sniper account.
10. Never signs or broadcasts transactions.

## What V9.0 intentionally does NOT claim

It does not yet identify every meme launch.
It does not yet know DEX liquidity.
It does not yet know actual token price.
It does not yet identify smart-money wallets from a historical dataset.
It does not yet execute paper buys because a verified DEX quote source is
not configured.

Those are deliberate gates.

## Next build: V9.1

Add verified Robinhood Chain DEX integrations:
- factory/pool discovery
- liquidity and reserve tracking
- swap quotes
- holder concentration
- Transfer event indexing
- wallet clustering
- Telegram alerts

Only after these are validated will the paper sniper become end-to-end.

## Run

```bash
pip install -r requirements-v9.txt
python v9_main.py
```

NO PRIVATE KEY.
NO LIVE ORDERS.
NO TRANSACTION SIGNING.
