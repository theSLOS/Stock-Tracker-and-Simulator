import pandas as pd


class StockPackage():
    def __init__(self, symbol,dfpath, name, lastUpdate=None):
        self.symbol = symbol
        self.name = name
        self.dfpath = dfpath
        self.df = self.load_data()
        if lastUpdate is None:
            self.lastUpdate = pd.Timestamp.now()
        else:
            self.lastUpdate = lastUpdate
    
    def __repr__(self):
        return f"StockInfo(symbol={self.symbol}, name={self.name}, sector={self.sector}, industry={self.industry})"
    def load_data(self):
        try:
            df = pd.read_csv(self.dfpath, parse_dates=True, index_col=0)
            return df
        except FileNotFoundError:
            print(f"Data file for {self.symbol} not found at {self.path}.")
            return pd.DataFrame()