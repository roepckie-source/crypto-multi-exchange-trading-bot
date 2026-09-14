# V9.1 DEX / Liquidity Intelligence
Robinhood Chain mainnet, chain ID 4663.

Verified Uniswap V3 deployment:
Factory: 0x1f7d7550b1b028f7571e69a784071f0205fd2efa
Position Manager: 0x73991a25c818bf1f1128deaab1492d45638de0d3
Swap Router: 0xcaf681a66d020601342297493863e78c959e5cb2
WETH: 0x0Bd7D308f8E1639FAb988df18A8011f41EAcAD73

V9.1 detects new Uniswap V3 pools, reads token metadata, pool liquidity and
slot0 price data, and provides holder-concentration infrastructure.

It does NOT execute trades, sign transactions, or use private keys.
USD liquidity, complete multi-DEX launch discovery, smart-money history and
paper execution against real swap quotes remain later gates.
