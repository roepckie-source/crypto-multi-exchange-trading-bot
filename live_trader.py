#!/usr/bin/env python3
import os
import sys
import csv
import time
import ccxt

# ==========================================
# KONFIGURATION & LOGGING
# ==========================================
RESULTS_FILE = "live_trading_results_real.csv"

# Mindest-Profit-Schwelle in Prozent (z. B. 0.8% für Profit nach Gebühren)
MIN_PROFIT_PCT = 0.8

# Handelsvolumen pro Arbitrage-Trade in USD
TRADE_AMOUNT_USD = 5.0

# Überwachter Krypto-Korb
SYMBOLS = [
    "NES/USDT", "RVN/USDT", "DFI/USDT", "DGB/USDT", "FLOKI/USDT",
    "KAS/USDT", "CFX/USDT", "ALPH/USDT", "CKB/USDT",
    "FET/USDT", "JASMY/USDT", "GALA/USDT", "VET/USDT", "STX/USDT",
    "PEPE/USDT", "BONK/USDT", "SHIB/USDT"
]

def init_csv():
    """ Erstellt die CSV-Datei mit Spaltenüberschriften, falls noch nicht vorhanden. """
    if not os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Timestamp", "Symbol", "Buy Exchange", "Sell Exchange", "Buy Price", "Sell Price", "Spread %", "Status / Details"])

def log_result(symbol, buy_ex, sell_ex, buy_price, sell_price, spread, status):
    """ Schreibt ein Handels- oder Status-Ergebnis in die CSV. """
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{symbol}] Spread: {spread:.2f}% ({buy_ex} -> {sell_ex}) | Status: {status}")
    with open(RESULTS_FILE, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([timestamp, symbol, buy_ex, sell_ex, f"{buy_price:.6f}", f"{sell_price:.6f}", f"{spread:.2f}", status])


# ==========================================
# PROTOKOLL & RUN-AUSWERTUNG (MIT GEWINN IN USD)
# ==========================================
def generate_run_summary(run_start_time):
    """ Analysiert die Ergebnisse des aktuellen Runs und gibt eine saubere Zusammenfassung inkl. USD-Gewinn aus. """
    print("\n" + "="*60)
    print("📊 LIVE TRADING RUN PROTOKOLL & AUSWERTUNG")
    print("="*60)
    
    if not os.path.exists(RESULTS_FILE):
        print("Keine Handelsdaten vorhanden.")
        return

    total_opportunities = 0
    successful_trades = 0
    failed_trades = 0
    total_spread_sum = 0.0
    total_profit_usd = 0.0
    symbols_traded = []

    with open(RESULTS_FILE, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                row_time = time.strptime(row["Timestamp"], "%Y-%m-%d %H:%M:%S")
                if row_time >= run_start_time:
                    total_opportunities += 1
                    status = row["Status / Details"]
                    spread = float(row["Spread %"])

                    if "SUCCESS" in status:
                        successful_trades += 1
                        total_spread_sum += spread
                        
                        # Gewinn in USD für diesen Trade berechnen
                        trade_profit = TRADE_AMOUNT_USD * (spread / 100.0)
                        total_profit_usd += trade_profit
                        
                        symbols_traded.append(f"{row['Symbol']} ({spread:.2f}% / +${trade_profit:.3f})")
                    else:
                        failed_trades += 1
            except Exception:
                continue

    avg_spread = (total_spread_sum / successful_trades) if successful_trades > 0 else 0.0

    print(f"⏱️ Zeitstempel:            {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🔍 Gefundene Gelegenheiten: {total_opportunities}")
    print(f"✅ Erfolgreiche Trades:     {successful_trades}")
    print(f"⚠️ Abgebrochene Orders:    {failed_trades}")
    if successful_trades > 0:
        print(f"📈 Ø Spread (Erfolgreich):  {avg_spread:.2f}%")
        print(f"💵 Erzielter Gewinn (USD):  +${total_profit_usd:.4f} USD")
        print(f"🎯 Gehandelte Paare:        {', '.join(symbols_traded)}")
    else:
        print("ℹ️ Keine vollständigen Arbitrage-Ausführungen in diesem Durchlauf.")
    print("="*60 + "\n")


# ==========================================
# BÖRSEN INITIALISIERUNG
# ==========================================
def init_exchanges():
    exchanges = {}

    okx_key = os.getenv("OKX_API_KEY")
    if okx_key:
        exchanges['okx'] = ccxt.okx({
            'apiKey': okx_key,
            'secret': os.getenv("OKX_API_SECRET"),
            'password': os.getenv("OKX_PASSPHRASE"),
            'enableRateLimit': True,
        })

    mexc_key = os.getenv("MEXC_API_KEY")
    if mexc_key:
        exchanges['mexc'] = ccxt.mexc({
            'apiKey': mexc_key,
            'secret': os.getenv("MEXC_API_SECRET"),
            'enableRateLimit': True,
        })

    bitrue_key = os.getenv("BITRUE_API_KEY")
    if bitrue_key:
        exchanges['bitrue'] = ccxt.bitrue({
            'apiKey': bitrue_key,
            'secret': os.getenv("BITRUE_API_SECRET"),
            'enableRateLimit': True,
        })

    return exchanges


# ==========================================
# AUTOMATISCHER COIN-TAUSCH & ARBITRAGE
# ==========================================
def ensure_coin_balance(exchange, symbol, base_coin, required_coin_amount):
    try:
        balance = exchange.fetch_balance()
        current_coin_balance = balance['total'].get(base_coin, 0.0) or balance['free'].get(base_coin, 0.0)

        if current_coin_balance >= required_coin_amount:
            return True, f"Genügend {base_coin} vorhanden ({current_coin_balance:.4f})"

        print(f"🔄 [{exchange.id}] Automatische Coin-Beschaffung: Kauft {base_coin} gegen USDT...")
        
        ticker = exchange.fetch_ticker(symbol)
        buy_price = ticker.get('ask', 0)
        if not buy_price or buy_price <= 0:
            return False, f"Fehler bei Auto-Kauf auf {exchange.id}: Kein gültiger Kaufpreis"
            
        usdt_needed = required_coin_amount * buy_price
        usdt_balance = balance['total'].get('USDT', 0.0) or balance['free'].get('USDT', 0.0)
        if usdt_balance < usdt_needed:
            return False, f"Fehlgeschlagen: Zu wenig USDT auf {exchange.id} ({usdt_balance:.2f} / {usdt_needed:.2f} USDT)"

        limit_buy_price = buy_price * 1.005
        try:
            buy_order = exchange.create_limit_buy_order(symbol, required_coin_amount, limit_buy_price)
        except Exception:
            buy_order = exchange.create_market_buy_order(symbol, required_coin_amount)

        order_id = buy_order.get('id')
        print(f"✅ [{exchange.id}] Auto-Kauf gesendet ID: {order_id}")
        
        for _ in range(4):
            time.sleep(1)
            bal = exchange.fetch_balance()
            if (bal['free'].get(base_coin, 0.0) or bal['total'].get(base_coin, 0.0)) >= (required_coin_amount * 0.9):
                return True, f"Auto-Kauf {base_coin} erfolgreich"

        if order_id:
            try:
                exchange.cancel_order(order_id, symbol)
                print(f"⚠️ [{exchange.id}] Auto-Kauf Order nicht sofort gefüllt – storniert.")
            except Exception:
                pass

        return False, f"Auto-Kauf auf {exchange.id} konnte nicht sofort ausgeführt werden (Orderbuch zu dünn)"

    except Exception as e:
        return False, f"Fehler bei Auto-Kauf auf {exchange.id}: {str(e)}"

def execute_arbitrage(buy_ex, sell_ex, symbol, buy_price, sell_price, spread):
    base_coin = symbol.split('/')[0]
    trade_quantity = TRADE_AMOUNT_USD / buy_price

    success, msg = ensure_coin_balance(sell_ex, symbol, base_coin, trade_quantity)
    if not success:
        log_result(symbol, buy_ex.id, sell_ex.id, buy_price, sell_price, spread, msg)
        return

    try:
        print(f"🚀 Starte Arbitrage: Kaufe {symbol} auf {buy_ex.id} & verkaufe auf {sell_ex.id}...")
        buy_order = buy_ex.create_market_buy_order(symbol, trade_quantity)
        
        actual_coin_balance = 0.0
        for _ in range(5):
            time.sleep(1)
            sell_balance = sell_ex.fetch_balance()
            actual_coin_balance = sell_balance['free'].get(base_coin, 0.0) or sell_balance['total'].get(base_coin, 0.0)
            if actual_coin_balance > 0:
                break

        sell_quantity = min(trade_quantity, actual_coin_balance)
        if sell_quantity <= 0:
            log_result(symbol, buy_ex.id, sell_ex.id, buy_price, sell_price, spread, f"Fehler: Guthaben auf {sell_ex.id} ist 0.0")
            return

        sell_order = sell_ex.create_market_sell_order(symbol, sell_quantity)
        status_msg = f"SUCCESS: Buy-ID {buy_order.get('id', 'N/A')} | Sell-ID {sell_order.get('id', 'N/A')}"
        log_result(symbol, buy_ex.id, sell_ex.id, buy_price, sell_price, spread, status_msg)

    except Exception as e:
        log_result(symbol, buy_ex.id, sell_ex.id, buy_price, sell_price, spread, f"Order-Fehler: {str(e)}")


# ==========================================
# HAUPTABLAUF
# ==========================================
def main():
    run_start_time = time.localtime()
    init_csv()
    exchanges = init_exchanges()

    if len(exchanges) < 2:
        print("❌ Mindestens 2 konfigurierte Börsen erforderlich!")
        sys.exit(1)

    print(f"🔍 Starte Preisabfrage für {len(SYMBOLS)} Handelspaare auf {list(exchanges.keys())}...")

    for symbol in SYMBOLS:
        tickers = {}
        for ex_name, ex in exchanges.items():
            try:
                tickers[ex_name] = ex.fetch_ticker(symbol)
            except Exception:
                continue

        if len(tickers) < 2:
            continue

        for buy_name, buy_ticker in tickers.items():
            for sell_name, sell_ticker in tickers.items():
                if buy_name == sell_name:
                    continue

                buy_price = buy_ticker.get('ask')
                sell_price = sell_ticker.get('bid')

                if not buy_price or not sell_price or buy_price <= 0 or sell_price <= 0:
                    continue

                spread_pct = ((sell_price - buy_price) / buy_price) * 100.0

                if spread_pct >= MIN_PROFIT_PCT:
                    buy_ex = exchanges[buy_name]
                    sell_ex = exchanges[sell_name]
                    execute_arbitrage(buy_ex, sell_ex, symbol, buy_price, sell_price, spread_pct)

    print("🏁 Live Trading Run abgeschlossen.")
    
    # Auswertung inkl. Gewinn in Dollar erzeugen
    generate_run_summary(run_start_time)

if __name__ == "__main__":
    main()
