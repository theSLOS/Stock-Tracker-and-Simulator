import pandas as pd
from dotenv import load_dotenv
import os
import datetime as dt
import yfinance as yf
import IndivStock


load_dotenv()
path = os.getenv('CSV_PATH')

def get_data(symbol, path):
    found = False
    while(not found):
        df = check_local(symbol, path)
        if df.empty:
            df = get_stock_data(symbol, path)
        else:
            print(f"Loaded data for {symbol} from local CSV.")

        if df.empty:
            print("No data available.")
            continue
        found = True

    print(df.head())
    return df

def get_stock_data(stock_symbol, path):
    print(f"Fetching data for {stock_symbol} from online source...\n")
    start = dt.datetime(2020, 1, 1)
    end = dt.datetime.now()
    df = yf.download(stock_symbol, start=start, end=end, auto_adjust=True)
    df.columns = df.columns.droplevel(1) if isinstance(df.columns, pd.MultiIndex) else df.columns
    df.sort_index(inplace=True)
    if not df.empty:
        df.to_csv(f"{path}/{stock_symbol}.csv")

    return df


def add_new_stock(stock_symbol, path, name=""):
    df = get_stock_data(stock_symbol, path)
    if df.empty:
        print(f"Failed to retrieve data for {stock_symbol}.")
        return None

    dfpath = f"{path}/{stock_symbol}.csv"
    stock_package = IndivStock.StockPackage(symbol=stock_symbol, dfpath=dfpath, name=name)
    return stock_package

def check_local(stock_symbol, path):
    try:
        df = pd.read_csv(f"{path}/{stock_symbol}.csv", parse_dates=True, index_col=0)
        return df
    except FileNotFoundError:
        return pd.DataFrame()