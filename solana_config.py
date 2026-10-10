
# Solana Smart-Money Wallet Intelligence
# PAPER ONLY. No private keys. No signing. No live orders.

CHAIN_NAME = "solana"
CLUSTER = "mainnet-beta"

# Public RPC endpoint. Apply conservative rate limits.
RPC_HTTP = "https://api.mainnet-beta.solana.com"
RPC_WSS = ""

# Configure only after verifying official program/mint addresses.
DEX_PROGRAM_IDS = []
QUOTE_MINTS = []

# Data collection
POLL_SECONDS = 2.0
MAX_EVENTS_PER_POLL = 100

# Wallet evaluation
MIN_CLOSED_TRADES = 10
MIN_WALLET_HISTORY_DAYS = 30
MAX_WALLET_SCORE = 100.0

# Paper account only
STARTING_PAPER_USDT = 35.47
PAPER_POSITION_USDT = 1.00

# Safety limits
MAX_DAILY_LOSS_PCT = 5.0
MAX_CONSECUTIVE_LOSSES = 3
MAX_POSITION_PCT = 0.05
MIN_LIQUIDITY_USD = 5_000.0

# Execution simulation
SIMULATED_FEE_RATE = 0.01
SIMULATED_SLIPPAGE_BPS = 100
SIMULATED_SIGNAL_DELAY_SECONDS = 5

# Hard execution lock
LIVE_TRADING_ENABLED = False
PRIVATE_KEY = ""
TRANSACTION_SIGNING_ENABLED = False
