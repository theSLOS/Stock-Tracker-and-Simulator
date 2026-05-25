import requests
from PyQt6.QtCore import QThread, pyqtSignal


class SenateWorker(QThread):
    finished = pyqtSignal(list)

    def __init__(self, symbol):
        super().__init__()
        self.symbol = symbol

    def run(self):
        try:
            resp = requests.get(
                f"https://senatestockwatcher.com/api/transactions?symbol={self.symbol}",
                timeout=10,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            if resp.status_code == 200:
                data = resp.json()
                self.finished.emit(data[:20] if data else [])
            else:
                self.finished.emit([])
        except Exception:
            self.finished.emit([])
