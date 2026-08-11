import time
import os
import csv
from datetime import datetime

from market_scanner import get_btc_prices, find_best_opportunity
from paper_trader import PaperTrader

SCAN_INTERVAL = 30
CSV_FILE = "trading_results.csv"

# ⏱️ 1 STUNDE LAUFZEIT: 60 Minuten * 2 Scans pro Minute (alle 30s) = 120 Scans
MAX_SCANS = 120  


def main():
    print("🚀 BTC MULTI-EXCHANGE PAPER TRADER", flush=True)
    print("🔥 VERSION 2026-08-11 - LIVE REAL DATA", flush=True)
    print("🤖 PAPER TRADING AKTIV (OHNE SIMULATION)", flush=True)
    print(f"⏱️ SCAN-INTERVALL: {SCAN_INTERVAL} SEKUNDEN")
    print(f"🛑 AUTOMATISCHER STOPP NACH: {MAX_SCANS} SCANS (1 STUNDE)\n", flush=True)

    # Initialisiere die Trading-Engine mit $100 Startkapital und 0.01% Mindestgewinn
    trader = PaperTrader(starting_balance=100.0, min_profit_percent=0.01)

    # CSV initialisieren und Spaltenköpfe schreiben falls Datei neu ist
    if not os.path.isfile(CSV_FILE):
        with open(CSV_FILE, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Zeitstempel", "Status", "Kauf_Boerse", "Verkauf_Boerse", "Netto_Prozent", "Profit_USD", "Kapital_Aktuell"])

    # Kontrollierte Schleife für exakt 1 Stunde Laufzeit
    while trader.scans < MAX_SCANS:
        aktuelle_runde = trader.scans + 1
        print("\n" + "=" * 65, flush=True)
        print(f"🔎 NEUER LIVE-SCAN ({aktuelle_runde}/{MAX_SCANS})", flush=True)
        print("=" * 65, flush=True)
        
        trader.register_scan()

        try:
            prices = get_btc_prices()
            if not prices:
                print("❌ KEINE LIVE-PREISE ERHALTEN", flush=True)
            else:
                opportunity = find_best_opportunity(prices)
                if opportunity:
                    # Trade auswerten (Prüft das reale herabgesetzte Limit von +0.01%)
                    was_executed = trader.evaluate_trade(opportunity)
                    
                    # Live in CSV dokumentieren
                    with open(CSV_FILE, mode='a', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        status = "AUSGEFUEHRT" if was_executed else "ABGELEHNT"
                        writer.writerow([
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            status,
                            opportunity.get("buy_exchange"),
                            opportunity.get("sell_exchange"),
                            opportunity.get("net_profit_percent"),
                            opportunity.get("net_profit"),
                            trader.balance
                        ])
                else:
                    print("\n⚪ KEINE LIVE ARBITRAGE-OPPORTUNITY GEFUNDEN", flush=True)

        except Exception as e:
            print(f"\n❌ FEHLER IM LIVE-SCAN-ABLAUF: {type(e).__name__}: {e}", flush=True)

        # Statistiken ausgeben
        try:
            trader.print_statistics()
        except Exception as e:
            print(f"⚠️ STATISTIK-FEHLER: {e}", flush=True)

        # Beim allerletzten Scan (Nummer 120) direkt beenden und die Wartezeit überspringen
        if trader.scans < MAX_SCANS:
            print(f"\n⏳ Nächster Live-Scan in {SCAN_INTERVAL} Sekunden...", flush=True)
            time.sleep(SCAN_INTERVAL)

    print("\n🏁 1-STÜNDIGER TESTLAUF BEENDET. Fahre geordnet herunter für Artefakt-Upload...", flush=True)


if __name__ == "__main__":
    main()
