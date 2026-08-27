name: Run Paper Trader (10 Min)

on:
  workflow_dispatch:
  schedule:
    - cron: '0 */6 * * *'

jobs:
  run-paper-trader:
    runs-on: ubuntu-latest
    timeout-minutes: 15

    steps:
      - name: Code auschecken
        uses: actions/checkout@v4

      - name: Python 3.12 einrichten
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Abhängigkeiten installieren
        run: |
          python -m pip install --upgrade pip
          pip install ccxt

      - name: Paper Trader ausführen (10 Minuten)
        env:
          PYTHONUNBUFFERED: "1"
          OKX_API_KEY: ${{ secrets.OKX_API_KEY }}
          OKX_API_SECRET: ${{ secrets.OKX_API_SECRET }}
          OKX_PASSPHRASE: ${{ secrets.OKX_PASSPHRASE }}
          KUCOIN_API_KEY: ${{ secrets.KUCOIN_API_KEY }}
          KUCOIN_API_SECRET: ${{ secrets.KUCOIN_API_SECRET }}
          KUCOIN_PASSPHRASE: ${{ secrets.KUCOIN_PASSPHRASE }}
          BITRUE_API_KEY: ${{ secrets.BITRUE_API_KEY }}
          BITRUE_API_SECRET: ${{ secrets.BITRUE_API_SECRET }}
        run: |
          python main_v4_test.py

      - name: Ergebnisse (CSV) speichern
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: paper-trading-results
          path: |
            paper_trading_results_v3.csv
            log_chancen_v3.csv
          if-no-files-found: ignore
          retention-days: 7
