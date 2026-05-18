import pandas as pd


class StockPackage:
    def __init__(self, symbol, dfpath, name, lastUpdate=None):
        self.symbol = symbol
        self.name = name
        self.dfpath = dfpath
        self.df = self.load_data()
        self.lastUpdate = lastUpdate if lastUpdate is not None else pd.Timestamp.now()

    def __repr__(self):
        return f"StockPackage(symbol={self.symbol}, name={self.name})"

    def load_data(self):
        try:
            return pd.read_csv(self.dfpath, parse_dates=True, index_col=0)
        except FileNotFoundError:
            print(f"Data file for {self.symbol} not found at {self.dfpath}.")
            return pd.DataFrame()
