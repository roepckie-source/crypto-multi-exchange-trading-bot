import os
import csv
import json
import urllib.request

class PaperTrader:
    def __init__(self, exchange_name="bitrue", amount=10.0, threshold=0.01, scans=30):
        self.exchange_name = exchange_name
        self.trade_amount_usdt = amount
        self.min_profit_threshold = threshold
        self.total_scans = scans
        
        self.telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
        
        # CSV-Datei zu Beginn neu anlegen und Header schreiben
        with open("trading_results.csv", mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["scan", "route", "profit_pct", "profit_usd", "accepted"])
            writer.writeheader()

    def send_telegram_message(self, message):
        if not self.telegram_token or not self.telegram_chat_id:
            return
            
        # Saubere URL-Formulierung
        token = self.telegram_token.strip()
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        
        payload = json.dumps({
            "chat_id": str(self.telegram_chat_id).strip(),
            "text": message,
            "parse_mode": "HTML"
        }).encode('utf-8')
        
        req = urllib.request.Request(
            url, 
            data=payload, 
            headers={'Content-Type': 'application/json'}
        )
        try:
            with urllib.request.urlopen(req) as response:
                pass
        except Exception as e:
            print(f"⚠️ Telegram-Fehler: {e}")

    def save_result_to_csv(self, result_dict):
        # Schreibt das Ergebnis sofort in die Datei, damit auch bei Abbruch Daten da sind
        with open("trading_results.csv", mode="a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["scan", "route", "profit_pct", "profit_usd", "accepted"])
            writer.writerow(result_dict)
