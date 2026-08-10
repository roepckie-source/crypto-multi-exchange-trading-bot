from market_scanner import get_btc_prices, find_best_opportunity

print("START BTC SCANNER", flush=True)

prices = get_btc_prices()

print("PREISE ERHALTEN", flush=True)

print(prices, flush=True)

opportunity = find_best_opportunity(prices)

print("OPPORTUNITY", flush=True)

print(opportunity, flush=True)

print("SCAN FERTIG", flush=True)
