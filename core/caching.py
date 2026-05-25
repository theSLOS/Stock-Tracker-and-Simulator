import os
import json
from datetime import datetime as dt

from core.stock_model import StockPackage


class CacheManager:
    def __init__(self, path: str):
        self.path = path
        self.data = self.load_cache()

    def list_stocks(self):
        return list(self.data.keys())

    def all_stocks(self):
        return dict(self.data)

    def has_stock(self, symbol: str) -> bool:
        return symbol in self.data

    def get_stock_data(self, symbol: str):
        return self.data.get(symbol, None)

    def set_stock_data(self, stock: StockPackage):
        self.data[stock.symbol] = {
            'name': stock.name,
            'symbol': stock.symbol,
            'dfpath': os.path.basename(stock.dfpath),
            'lastUpdate': stock.lastUpdate.isoformat()
        }
        self.save_cache()

    def delete_stock(self, symbol: str, csv_path: str):
        if symbol in self.data:
            os.remove(os.path.join(csv_path, self.data[symbol]['dfpath']))
            del self.data[symbol]
            self.save_cache()

    def save_cache(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f, indent=4)

    def load_cache(self):
        if not os.path.exists(self.path):
            with open(self.path, 'w') as f:
                json.dump({}, f, indent=4)
        with open(self.path, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}

    def clear_cache(self):
        self.data = {}
        self.save_cache()

    def get_last_update(self, symbol: str):
        entry = self.get_stock_data(symbol)
        if entry is None:
            return None
        last_update_str = entry.get('lastUpdate')
        if last_update_str is None:
            return None
        return dt.fromisoformat(last_update_str)

    def is_stock_fresh(self, symbol: str, days: int = 1) -> bool:
        last_update = self.get_last_update(symbol)
        if last_update is None:
            return False
        return (dt.now() - last_update).days < days

    def update_stock_timestamp(self, symbol: str):
        entry = self.get_stock_data(symbol)
        if entry is not None:
            entry['lastUpdate'] = dt.now().isoformat()
            self.save_cache()

    def get_ai_analysis(self, symbol: str):
        entry = self.data.get(symbol)
        if entry is None:
            return None
        return entry.get('ai_analysis')

    def set_ai_analysis(self, symbol: str, result: dict):
        entry = self.data.get(symbol)
        if entry is None:
            return
        entry['ai_analysis'] = {
            'timestamp': dt.now().isoformat(),
            'score': result.get('score'),
            'pros': result.get('pros', []),
            'cons': result.get('cons', [])
        }
        self.save_cache()

    def is_ai_analysis_fresh(self, symbol: str, hours: int = 24) -> bool:
        analysis = self.get_ai_analysis(symbol)
        if not analysis:
            return False
        timestamp_str = analysis.get('timestamp')
        if not timestamp_str:
            return False
        return (dt.now() - dt.fromisoformat(timestamp_str)).total_seconds() < hours * 3600

    def display_cache(self):
        import json
        print(json.dumps(self.data, indent=4))
