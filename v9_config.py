# V9 Meme Sniper / On-Chain Intelligence
# PAPER ONLY. No private keys. No transaction signing. No live execution.

CHAIN_NAME = "robinhood"
CHAIN_ID = 4663
RPC_HTTP = "https://rpc.mainnet.chain.robinhood.com"
# Use a provider WSS URL for real-time production-like monitoring.
RPC_WSS = ""

# Optional DEX factory addresses.
# Leave empty until verified from the official DEX deployment docs.
DEX_FACTORIES = []

# Stablecoins / quote assets can be added after deployment addresses are verified.
QUOTE_TOKENS = []

# Scanner settings
POLL_SECONDS = 2.0
BLOCK_LOOKBACK = 1
MAX_NEW_CONTRACTS_PER_BLOCK = 100

# Paper account only
STARTING_PAPER_USDT = 35.47
PAPER_POSITION_USDT = 1.00

# Hard risk vetoes
MAX_TOP_HOLDER_SHARE_PCT = 20.0
MAX_DEV_SHARE_PCT = 10.0
MIN_LIQUIDITY_USDT = 5_000.0

# Scoring thresholds
PAPER_BUY_SCORE = 80
WATCH_SCORE = 65

# No real execution in V9.
LIVE_TRADING_ENABLED = False
PRIVATE_KEY_ENV = ""

# Optional Telegram alerts. Keep empty for now.
TELEGRAM_BOT_TOKEN = ""
TELEGRAM_CHAT_ID = ""
UNISWAP_V3_FACTORY="0x1f7d7550b1b028f7571e69a784071f0205fd2efa"
UNISWAP_V3_POSITION_MANAGER="0x73991a25c818bf1f1128deaab1492d45638de0d3"
UNISWAP_V3_SWAP_ROUTER="0xcaf681a66d020601342297493863e78c959e5cb2"
WETH="0x0Bd7D308f8E1639FAb988df18A8011f41EAcAD73"
