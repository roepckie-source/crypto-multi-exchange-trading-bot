import os
import sys
from paper_trader import PaperTrader

def main():
    print("=" * 65)
    print("🚀 CRYPTO TRADING BOT - PAPER TRADING LAUNCHER")
    print("=" * 65)

    # Configuration (uses environment variables if present, otherwise defaults)
    exchange_name = os.getenv("EXCHANGE_NAME", "bitrue")
    trade_amount = float(os.getenv("TRADE_AMOUNT", "10.0"))     # $10 / 10 € stake
    min_threshold = float(os.getenv("MIN_THRESHOLD", "0.01"))   # Min. profit 0.01%
    total_scans = int(os.getenv("TOTAL_SCANS", "10"))           # Number of scans per run

    print(f"Börse:            {exchange_name.upper()}")
    print(f"Einsatz pro Trade: ${trade_amount:.2f}")
    print(f"Min. Schwelle:    {min_threshold:.2f}%")
    print(f"Anzahl Scans:     {total_scans}")
    print("=" * 65 + "\n")

    try:
        # Initialize and run PaperTrader
        bot = PaperTrader(
            exchange_name=exchange_name,
            amount=trade_amount,
            threshold=min_threshold,
            scans=total_scans
        )
        bot.run()
        print("\n🎉 Durchlauf erfolgreich beendet.")
    except Exception as e:
        print(f"\n❌ Fehler bei der Ausführung des Bots: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
