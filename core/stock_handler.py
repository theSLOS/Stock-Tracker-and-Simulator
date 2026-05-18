import os
import datetime as dt

import pandas as pd
import yfinance as yf
from dotenv import load_dotenv

from core.stock_model import StockPackage

load_dotenv()


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
    return StockPackage(symbol=stock_symbol, dfpath=dfpath, name=name)


def check_local(stock_symbol, path):
    try:
        return pd.read_csv(f"{path}/{stock_symbol}.csv", parse_dates=True, index_col=0)
    except FileNotFoundError:
        return pd.DataFrame()


def calculate_SMA(df, window):
    return df['Close'].rolling(window=window).mean()


def calculate_EMA(df, window):
    return df['Close'].ewm(span=window, adjust=False).mean()
