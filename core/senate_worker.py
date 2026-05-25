import os

import requests
from PyQt6.QtCore import QThread, pyqtSignal

_CODE_MAP = {"P": "Purchase", "S": "Sale", "A": "Award", "D": "Disposition", "G": "Gift", "F": "Tax Withholding"}


class SenateWorker(QThread):
    finished = pyqtSignal(list)

    def __init__(self, symbol):
        super().__init__()
        self.symbol = symbol

    def run(self):
        try:
            api_key = os.getenv("FINNHUB_API_KEY")
            if not api_key:
                self.finished.emit([])
                return
            resp = requests.get(
                f"https://finnhub.io/api/v1/stock/insider-transactions?symbol={self.symbol}&token={api_key}",
                timeout=10,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            if resp.status_code != 200:
                self.finished.emit([])
                return
            raw = resp.json().get("data", [])
            trades = []
            for t in raw[:20]:
                code = t.get("transactionCode", "")
                trade_type = _CODE_MAP.get(code, code)
                shares = abs(t.get("change", 0))
                price = t.get("transactionPrice", 0)
                amount = f"{shares:,.0f} shares" + (f" @ ${price:.2f}" if price else "")
                trades.append({
                    "name": t.get("name", "Unknown"),
                    "type": trade_type,
                    "transaction_date": t.get("transactionDate", ""),
                    "amount": amount
                })
            self.finished.emit(trades)
        except Exception:
            self.finished.emit([])
