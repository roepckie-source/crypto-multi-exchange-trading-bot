import time
import sys
from datetime import datetime, timedelta

# Importiere deine bestehende Engine & Rebalancer Logik
try:
    from rebalancer import check_and_rebalance
    from arbitrage_engine_v2 import run_arbitrage_engine
except ImportError:
    pass

def execute_single_run():
    """
    Führt einen einzelnen Trading- & Rebalance-Durchlauf aus.
    Gibt die Statistik des Durchlaufs als Dictionary zurück.
    """
    stats = {
        "opportunities": 0,
        "success": 0,
        "failed": 0,
        "profit_usd": 0.0,
        "pairs": []
    }
    
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ⚖️ Starte Rebalancing & Arbitrage-Prüfung...")
    
    try:
        # 1. Aufruf deiner Rebalancing-Funktion aus rebalancer.py
        rebalance_result = check_and_rebalance()
        
        # Falls check_and_rebalance() Daten zurückgibt, hier verarbeiten:
        if isinstance(rebalance_result, dict):
            stats["opportunities"] += rebalance_result.get("opportunities", 0)
            stats["success"] += rebalance_result.get("success", 0)
            stats["failed"] += rebalance_result.get("failed", 0)
            stats["profit_usd"] += rebalance_result.get("profit_usd", 0.0)
            if "pairs" in rebalance_result:
                stats["pairs"].extend(rebalance_result["pairs"])

        # 2. Kurze Pause nach den API-Abfragen einbauen (schützt vor IP-Sperren)
        time.sleep(1.5)

    except Exception as e:
        print(f"❌ Fehler während des Durchlaufs: {e}")
        stats["failed"] += 1
        
    return stats

def run_24h_cycle():
    """
    Läuft exakt 24 Stunden lang, führt alle 10 Minuten einen Trade-Check aus,
    aggregiert die Tagesergebnisse und gibt am Ende einen Bericht aus.
    """
    start_time = datetime.now()
    end_time = start_time + timedelta(hours=24)
    
    daily_summary = {
        "total_runs": 0,
        "total_opportunities": 0,
        "total_success": 0,
        "total_failed": 0,
        "total_profit_usd": 0.0,
        "traded_pairs": set()
    }

    print("\n" + "="*60)
    print("🚀 STARTE 24-STUNDEN TRADING-ZYKLUS")
    print(f"⏱️ Startzeit: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🏁 Geplantes Ende: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    while datetime.now() < end_time:
        daily_summary["total_runs"] += 1
        print(f"\n--- Durchlauf #{daily_summary['total_runs']} ---")
        
        # Einzellauf ausführen
        run_stats = execute_single_run()
        
        # Ergebnisse in Tagesstatistik aufsummieren
        daily_summary["total_opportunities"] += run_stats.get("opportunities", 0)
        daily_summary["total_success"] += run_stats.get("success", 0)
        daily_summary["total_failed"] += run_stats.get("failed", 0)
        daily_summary["total_profit_usd"] += run_stats.get("profit_usd", 0.0)
        
        for pair in run_stats.get("pairs", []):
            daily_summary["traded_pairs"].add(pair)

        # Berechne verbleibende Zeit im 24h-Fenster
        remaining_seconds = (end_time - datetime.now()).total_seconds()
        if remaining_seconds <= 0:
            break

        # Wartezeit für das Intervall (10 Minuten = 600 Sekunden)
        sleep_time = min(600, remaining_seconds)
        print(f"⏳ Nächster Scan in {int(sleep_time / 60)} Minuten...")
        time.sleep(sleep_time)

    # ============================================================
    # 📊 24-STUNDEN TAGESAUSWERTUNG
    # ============================================================
    print("\n" + "="*60)
    print("📊 LIVE-HANDEL 24-STUNDEN TAGESBERICHT & AUSWERTUNG")
    print("="*60)
    print(f"⏱️ Zeitspanne:           {start_time.strftime('%Y-%m-%d %H:%M')} bis {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"🔄 Absolvierte Runs:     {daily_summary['total_runs']}")
    print(f"🔍 Gefundene Chancen:    {daily_summary['total_opportunities']}")
    print(f"✅ Erfolgreiche Trades:  {daily_summary['total_success']}")
    print(f"⚠️ Abgebrochene Orders:  {daily_summary['total_failed']}")
    print(f"💵 Gesamtgewinn (USD):   +${daily_summary['total_profit_usd']:.4f} USD")
    print(f"🎯 Gehandelte Paare:     {', '.join(daily_summary['traded_pairs']) if daily_summary['traded_pairs'] else 'Keine'}")
    print("="*60 + "\n")

if __name__ == "__main__":
    while True:
        try:
            run_24h_cycle()
        except KeyboardInterrupt:
            print("\n🛑 Bot wurde manuell vom Benutzer gestoppt.")
            sys.exit()
        except Exception as e:
            print(f"💥 Unerwarteter Systemfehler im 24h-Hauptloop: {e}")
            print("🔄 Starte Loop in 30 Sekunden neu...")
            time.sleep(30)
