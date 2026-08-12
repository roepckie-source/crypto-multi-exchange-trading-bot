from paper_trader import PaperTrader

def main():
    # Startet das reparierte All-in-One-Skript mit $100 Einsatz und 0.01% Hürde
    # Die Anzahl der Scans (1800) ist fest in deiner paper_trader.py definiert
    trader = PaperTrader(amount=100.0, threshold=0.01)
    trader.run()

if __name__ == "__main__":
    main()
