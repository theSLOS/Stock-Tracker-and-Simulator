import os
import json
import IndivStock
from datetime import datetime as dt

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
    
    def set_stock_data(self, stock: IndivStock.StockPackage):
        entry = {
            'name': stock.name, 
            'symbol': stock.symbol,
            'dfpath': stock.dfpath,
            'lastUpdate': stock.lastUpdate.isoformat()
        }
        self.data[stock.symbol] = entry
        self.save_cache()

    def delete_stock(self, symbol: str):
        if symbol in self.data:
            os.remove(f"{self.data[symbol]['dfpath']}")
            del self.data[symbol]
            self.save_cache()

    def display_cache(self):
        print(json.dumps(self.data, indent=4))

    def save_cache(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f, indent=4)
    

    def load_cache(self):
        if not os.path.exists(self.path):
            with open(self.path, 'w') as f:
                json.dump({}, f, indent=4)
    
        with open(self.path, 'r') as f:
            try:
                cache = json.load(f)
            except json.JSONDecodeError:
                cache = {}
        return cache
    
    def clear_cache(self):
        self.data = {}
        self.save_cache()

    def get_last_update(self, symbol: str):
        entry = self.get_stock_data(symbol)
        if entry is None:
            return None
        last_update_str = entry.get('lastUpdate', None)
        if last_update_str is None:
            return None
    
        return dt.fromisoformat(last_update_str)
    
    def is_stock_fresh(self, symbol: str, days: int = 1) -> bool:
        last_update = self.get_last_update(symbol)
        if last_update is None:
            return False
        delta = dt.now() - last_update
        return delta.days < days

    def update_stock_timestamp(self, symbol: str):
        entry = self.get_stock_data(symbol)
        if entry is not None:
            entry['lastUpdate'] = dt.now().isoformat()
            self.save_cache()