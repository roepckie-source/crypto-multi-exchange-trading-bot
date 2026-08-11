import time
import os
import csv
from datetime import datetime

from market_scanner import get_btc_prices, find_best_opportunity
from paper_trader import PaperTrader

SCAN_INTERVAL = 10  # Schnellerer Takt, da nur 1 Börse gescannt wird
CSV_FILE = "trading_results.csv"
MAX_SCANS = 360  # 360 Scans * 10 Sekunden = Exakt 1 Stunde Laufzeit


def main():
    print("🚀 BITRUE TRIANGULAR ARBITRAGE TRADER", flush=True)
    print("🔥 VERSION 2026-08-11 - INTERNAL MATRIX", flush=True)
    print(f"⏱️ INTERVAL: {SCAN_INTERVAL}s | DAUER: {MAX_SCANS} SCANS (1 STD)\n", flush=True)

    trader = PaperTrader(starting_balance=100.0, min_profit_percent=0.01)

    if not os.path.isfile(CSV_FILE):
        with open(CSV_FILE, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Zeitstempel", "Status", "Route", "Netto_Prozent", "Profit_USD", "Kapital_Aktuell"])

    while trader.scans < MAX_SCANS:
        print("\n" + "=" * 65, flush=True)
        print(f"🔎 SCAN ({trader.scans + 1}/{MAX_SCANS})", flush=True)
        print("=" * 65, flush=True)
        
        trader.register_scan()

        try:
            prices = get_btc_prices()
            if prices:
                opportunity = find_best_opportunity(prices, trade_size=100.0)
                if opportunity:
                    was_executed = trader.evaluate_trade(opportunity)
                    
                    with open(CSV_FILE, mode='a', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        status = "AUSGEFUEHRT" if was_executed else "ABGELEHNT"
                        writer.writerow([
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            status,
                            f"USDT-{opportunity.get('coin')}-BTC-USDT",
                            opportunity.get("net_profit_percent"),
                            opportunity.get("net_profit"),
                            trader.balance
                        ])
        except Exception as e:
            print(f"❌ SCHLEIFEN-FEHLER: {e}", flush=True)

        trader.print_statistics()
        
        if trader.scans < MAX_SCANS:
            time.sleep(SCAN_INTERVAL)

    print("\n🏁 1-STÜNDIGER BITRUE-LAUF BEENDET. Artefakt wird bereitgestellt...", flush=True)


if __name__ == "__main__":
    main()
