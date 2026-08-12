import ccxt
import time
import csv
import urllib.request
import urllib.parse

# ============================================================
# TELEGRAM KONFIGURATION (Hier deine Daten eintragen)
# ============================================================
# Ersetze die Punkte unten durch deinen echten langen Token vom BotFather!
TELEGRAM_TOKEN = "123456789:ABCdefGhIJKlmNoPQ..." 
TELEGRAM_CHAT_ID = "1986780629"

class PaperTrader:
    def __init__(self, exchange_name="bitrue", amount=100.0, threshold=0.01, scans=1800):
        self.exchange_name = exchange_name
        self.trade_amount_usdt = amount
        self.min_profit_threshold = threshold
        self.taker_fee = 0.00098  # Exakte Bitrue Standard-Fee (0.098%)
        self.total_scans = scans
        
        self.exchange = getattr(ccxt, exchange_name)({'enableRateLimit': True})
        
        # Bereinigte Routen passend zu den echten Bitrue-Symbolen
        # Format: (Coin_A, Coin_B) -> Route läuft immer: USDT -> Coin_A -> Coin_B -> USDT
        self.routes = [
            {"coin_a": "DFI", "coin_b": "BTC"},
            {"coin_a": "XRP", "coin_b": "BTC"},
            {"coin_a": "ETH", "coin_b": "BTC"},
            {"coin_a": "LTC", "coin_b": "BTC"},
        ]

    def send_telegram_message(self, text):
        if not TELEGRAM_TOKEN or "HIER_" in TELEGRAM_TOKEN: return
        url = f"https://telegram.org{TELEGRAM_TOKEN}/sendMessage"
        data = urllib.parse.urlencode({"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}).encode("utf-8")
        try:
            req = urllib.request.Request(url, data=data)
            with urllib.request.urlopen(req, timeout=5) as response: pass
        except Exception as e:
            print(f"⚠️ Telegram-Fehler: {e}", flush=True)

    def evaluate_triangular(self, coin_a, coin_b, amount):
        try:
            # Lade alle 3 benötigten Ticker parallel für exakte Gleichzeitigkeit
            tickers = self.exchange.fetch_tickers([f"{coin_a}/USDT", f"{coin_b}/{coin_a}", f"{coin_b}/USDT"])
            
            p1 = f"{coin_a}/USDT"
            p2 = f"{coin_b}/{coin_a}"
            p3 = f"{coin_b}/USDT"
            
            if not (p1 in tickers and p2 in tickers and p3 in tickers): return None
            
            # Schritt 1: USDT -> Coin_A (Wir KAUFEN Coin_A zum Ask-Preis)
            ask1 = float(tickers[p1]['ask'])
            if ask1 <= 0: return None
            amount_a = (amount / ask1) * (1 - self.taker_fee)
            
            # Schritt 2: Coin_A -> Coin_B (Wir KAUFEN Coin_B mit Coin_A zum Ask-Preis)
            ask2 = float(tickers[p2]['ask'])
            if ask2 <= 0: return None
            amount_b = (amount_a / ask2) * (1 - self.taker_fee)
            
            # Schritt 3: Coin_B -> USDT (Wir VERKAUFEN Coin_B zurück in USDT zum Bid-Preis)
            bid3 = float(tickers[p3]['bid'])
            final_usdt = (amount_b * bid3) * (1 - self.taker_fee)
            
            profit_pct = ((final_usdt - amount) / amount) * 100
            profit_usd = final_usdt - amount
            return profit_pct, profit_usd
        except Exception:
            return None

    def run(self):
        results = []
        print(f"🚀 Highspeed Dreiecks-Trader auf {self.exchange_name.upper()} gestartet.")
        print(f"⏱️ Scans: {self.total_scans} | Einsatz: ${self.trade_amount_usdt:.2f} | Limit: {self.min_profit_threshold}%\n", flush=True)
        
        # Kleine Test-Nachricht beim Starten an dein Handy senden
        self.send_telegram_message("🤖 *Bitrue Turbo-Bot erfolgreich gestartet!* Suche nach Dreiecks-Arbitrage...")

        for scan in range(1, self.total_scans + 1):
            if scan % 50 == 0 or scan == 1:
                print(f"⚡ Scan-Fortschritt: {scan}/{self.total_scans}", flush=True)
                
            for r in self.routes:
                res = self.evaluate_triangular(r["coin_a"], r["coin_b"], self.trade_amount_usdt)
                if res:
                    pct, usd = res
                    route_str = f"USDT -> {r['coin_a']} -> {r['coin_b']} -> USDT"
                    
                    # Nur Gewinne oder Status-Updates alle 100 Runden im Log anzeigen (schont die GitHub-Konsole)
                    if pct >= self.min_profit_threshold or (scan % 100 == 0 and r["coin_a"] == "DFI"):
                        print(f"🔄 Pfad: {route_str:<32} | Netto: {pct:+.4f}%", flush=True)
                    
                    if pct >= self.min_profit_threshold:
                        print(f"🟢 PROFITAPLER INSTANT-HIT! Sende Telegram...", flush=True)
                        msg = (
                            f"💰 *BITRUE ARBITRAGE HIT!*\n\n"
                            f"🔄 *Route:* {route_str}\n"
                            f"📈 *Rendite:* +{pct:.4f}%\n"
                            f"💵 *Gewinn:* +${usd:,.4f}"
                        )
                        self.send_telegram_message(msg)
                    
                    results.append({
                        "scan": scan,
                        "route": route_str,
                        "profit_pct": round(pct, 4),
                        "profit_usd": round(usd, 4),
                        "accepted": pct >= self.min_profit_threshold
                    })
            time.sleep(2) # 2 Sekunden Highspeed-Intervall
                
        # CSV-Ergebnisse schreiben
        with open("trading_results.csv", mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["scan", "route", "profit_pct", "profit_usd", "accepted"])
            writer.writeheader()
            writer.writerows(results)
            
        print("\n✅ Analyse abgeschlossen. Ergebnisse in 'trading_results.csv' gespeichert.")


if __name__ == "__main__":
    trader = PaperTrader()
    trader.run()
