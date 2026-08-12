import time
import os
import csv
from datetime import datetime

from market_scanner import get_btc_prices, find_best_opportunity
from paper_trader import PaperTrader

# ⏱️ HIGH-SPEED SETTINGS: Alle 2 Sekunden ein Scan
SCAN_INTERVAL = 2  
CSV_FILE = "trading_results.csv"
MAX_SCANS = 1800  # 1800 Scans * 2 Sekunden = Exakt 1 Stunde Laufzeit


def main():
    print("🚀 BITRUE HIGH-SPEED TRIANGULAR TRADER", flush=True)
    print("🔥 VERSION 2026-08-12 - TURBO MATRIX", flush=True)
    print(f"⏱️ INTERVAL: {SCAN_INTERVAL}s | DAUER: {MAX_SCANS} SCANS (1 STD)\n", flush=True)

    trader = PaperTrader(starting_balance=100.0, min_profit_percent=0.01)

    if not os.path.isfile(CSV_FILE):
        with open(CSV_FILE, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Zeitstempel", "Status", "Route", "Netto_Prozent", "Profit_USD", "Kapital_Aktuell"])

    while trader.scans < MAX_SCANS:
        if (trader.scans + 1) % 10 == 0 or trader.scans == 0:
            print(f"⚡ SCAN PROGRESS: ({trader.scans + 1}/{MAX_SCANS})", flush=True)
        
        trader.register_scan()

        try:
            prices = get_btc_prices()
            if prices:
                opportunity = find_best_opportunity(prices, trade_size=100.0)
                if opportunity:
                    was_executed = trader.evaluate_trade(opportunity)
                    
                    if was_executed:
                        with open(CSV_FILE, mode='a', newline='', encoding='utf-8') as f:
                            writer = csv.writer(f)
                            writer.writerow([
                                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "AUSGEFUEHRT",
                                f"USDT-{opportunity.get('coin')}-BTC-USDT",
                                opportunity.get("net_profit_percent"),
                                opportunity.get("net_profit"),
                                trader.balance
                            ])
        except Exception as e:
            pass # Fängt kurze Netzwerk-Lags im Highspeed-Modus lautlos ab

        if was_executed or (trader.scans % 150 == 0):
            trader.print_statistics()
        
        if trader.scans < MAX_SCANS:
            time.sleep(SCAN_INTERVAL)

    print("\n🏁 HIGH-SPEED LAUF BEENDET. Generiere Excel-Artefakt...", flush=True)


if __name__ == "__main__":
    main()
