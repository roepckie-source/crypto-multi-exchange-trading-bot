import os
import sys
import time

try:
    import ccxt
except ImportError:
    ccxt = None

# ============================================================
# ⚙️ REBALANCER KONFIGURATION
# ============================================================

# True = Berechnet Transfers & simuliert nur (SICHER).
# False = Führt echte On-Chain Auszahlungen durch (ACHTUNG: Auszahlungs-Rechte beim API-Key nötig!)
SIMULATION_MODE = True

# Mindestabweichung vom Zielguthaben (in USD), ab der ein Transfer ausgelöst wird
MIN_REBALANCE_THRESHOLD_USD = 10.0

# Bevorzugtes Blockchain-Netzwerk für USDT-Transfers ('TRX' für TRC20, 'MATIC' für Polygon)
PREFERRED_NETWORK = "TRX"

# ============================================================
# 🏦 BÖRSEN-INITIALISIERUNG
# ============================================================


def init_exchanges():
    """Initialisiert die Börsenverbindungen für das Rebalancing."""
    exchanges = {}
    if not ccxt:
        print("⚠️ CCXT ist nicht installiert!")
        return exchanges

    # OKX (Inklusive EEA-Fix für EU-Accounts)
    okx_key, okx_sec, okx_pass = (
        os.getenv("OKX_API_KEY"),
        os.getenv("OKX_API_SECRET"),
        os.getenv("OKX_PASSPHRASE"),
    )
    if okx_key and okx_sec and okx_pass:
        try:
            exchanges["okx"] = ccxt.okx(
                {
                    "apiKey": okx_key,
                    "secret": okx_sec,
                    "password": okx_pass,
                    "hostname": "my.okx.com",
                    "enableRateLimit": True,
                }
            )
        except Exception as e:
            print(f"❌ Fehler bei OKX: {e}")

    # MEXC
    mexc_key, mexc_sec = os.getenv("MEXC_API_KEY"), os.getenv("MEXC_API_SECRET")
    if mexc_key and mexc_sec:
        try:
            exchanges["mexc"] = ccxt.mexc(
                {"apiKey": mexc_key, "secret": mexc_sec, "enableRateLimit": True}
            )
        except Exception as e:
            print(f"❌ Fehler bei MEXC: {e}")

    # BITRUE
    bit_key, bit_sec = os.getenv("BITRUE_API_KEY"), os.getenv("BITRUE_API_SECRET")
    if bit_key and bit_sec:
        try:
            exchanges["bitrue"] = ccxt.bitrue(
                {"apiKey": bit_key, "secret": bit_sec, "enableRateLimit": True}
            )
        except Exception as e:
            print(f"❌ Fehler bei BITRUE: {e}")

    # KUCOIN
    kuc_key, kuc_sec, kuc_pass = (
        os.getenv("KUCOIN_API_KEY"),
        os.getenv("KUCOIN_API_SECRET"),
        os.getenv("KUCOIN_PASSPHRASE"),
    )
    if kuc_key and kuc_sec and kuc_pass:
        try:
            exchanges["kucoin"] = ccxt.kucoin(
                {
                    "apiKey": kuc_key,
                    "secret": kuc_sec,
                    "password": kuc_pass,
                    "enableRateLimit": True,
                }
            )
        except Exception as e:
            print(f"❌ Fehler bei KuCoin: {e}")

    return exchanges


# ============================================================
# 🧮 REBALANCING ALGORITHMUS LOGIK
# ============================================================


def calculate_rebalance_plan(balances):
    """Berechnet mathematisch den optimalen Transfer-Plan zwischen allen Börsen."""
    total_usdt = sum(balances.values())
    num_exchanges = len(balances)

    if num_exchanges == 0:
        return [], 0, 0

    target_per_exchange = total_usdt / num_exchanges

    senders = {}
    receivers = {}

    for name, amount in balances.items():
        diff = amount - target_per_exchange
        if diff > MIN_REBALANCE_THRESHOLD_USD:
            senders[name] = diff
        elif diff < -MIN_REBALANCE_THRESHOLD_USD:
            receivers[name] = abs(diff)

    transfers = []

    # Greedy-Algorithmus zur Zuordnung von Sendern an Empfänger
    for rec_name, rec_needed in list(receivers.items()):
        needed = rec_needed
        for send_name, send_avail in list(senders.items()):
            if send_avail <= 0 or needed <= 0:
                continue

            amount_to_send = min(send_avail, needed)

            transfers.append(
                {
                    "from": send_name,
                    "to": rec_name,
                    "amount": round(amount_to_send, 2),
                }
            )

            senders[send_name] -= amount_to_send
            needed -= amount_to_send

    return transfers, total_usdt, target_per_exchange


# ============================================================
# 🚀 AUSFÜHRUNG DER TRANSFERS
# ============================================================


def execute_rebalance():
    print("⚖️ Starte Rebalancing-Prüfung...")
    exchanges = init_exchanges()

    if not exchanges:
        print("❌ Keine Börsenverbindungen verfügbar.")
        return

    balances = {}
    for name, exchange in exchanges.items():
        try:
            balance_data = exchange.fetch_balance()
            usdt_free = 0.0
            if "USDT" in balance_data:
                usdt_free = float(balance_data["USDT"].get("free", 0.0))
            elif "free" in balance_data and "USDT" in balance_data["free"]:
                usdt_free = float(balance_data["free"]["USDT"])

            balances[name] = usdt_free
            print(f"💰 [{name.upper()}] Verfügbares USDT: {usdt_free:.2f}")
        except Exception as e:
            print(f"❌ Fehler beim Abfragen von {name}: {e}")

    if not balances:
        return

    transfers, total_usdt, target_amount = calculate_rebalance_plan(balances)

    print("\n" + "=" * 55)
    print("📊 REBALANCING STATUS & BERECHNUNG")
    print(f"Gesamt-USDT über alle Börsen:  ${total_usdt:.2f}")
    print(f"Ziel-Guthaben pro Börse:      ${target_amount:.2f}")
    print("=" * 55)

    if not transfers:
        print(
            f"✅ Keine Rebalancing-Aktion nötig. Alle Börsen liegen innerhalb der Toleranz (±${MIN_REBALANCE_THRESHOLD_USD:.2f})."
        )
        return

    print(f"\n🔄 BERECHNETER TRANSFER-PLAN ({len(transfers)} Aktionen):")
    for t in transfers:
        print(
            f"  ➔ Sende ${t['amount']:.2f} USDT von {t['from'].upper()} nach {t['to'].upper()}"
        )

    print("\n-------------------------------------------------------")

    for t in transfers:
        sender_name = t["from"]
        receiver_name = t["to"]
        amount = t["amount"]

        if SIMULATION_MODE:
            print(
                f"🧪 [SIMULATION] WÜRDE AUSFÜHREN: ${amount:.2f} USDT von {sender_name.upper()} ➔ {receiver_name.upper()} (Netzwerk: {PREFERRED_NETWORK})"
            )
        else:
            try:
                rec_ex = exchanges[receiver_name]
                sender_ex = exchanges[sender_name]

                # Einzahlungsadresse des Empfängers abrufen
                dep_info = rec_ex.fetch_deposit_address(
                    "USDT", params={"network": PREFERRED_NETWORK}
                )
                address = dep_info["address"]
                tag = dep_info.get("tag", None)

                print(
                    f"🚀 ECHTE AUSZAHLUNG: Sende ${amount:.2f} USDT von {sender_name.upper()} an {address} ({PREFERRED_NETWORK})..."
                )

                withdraw_res = sender_ex.withdraw(
                    code="USDT",
                    amount=amount,
                    address=address,
                    tag=tag,
                    params={"network": PREFERRED_NETWORK},
                )

                print(
                    f"✅ Transaktion übermittelt! ID: {withdraw_res.get('id', 'N/A')}"
                )
            except Exception as e:
                print(
                    f"❌ Fehler bei Ausführung ({sender_name} ➔ {receiver_name}): {e}"
                )


if __name__ == "__main__":
    execute_rebalance()
