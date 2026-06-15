import os
import json
from datetime import date as _date
from PyQt6.QtCore import QThread, pyqtSignal

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CACHE_PATH = os.path.join(_PROJECT_ROOT, "Users", "explore_cache.json")

# Fallback universe used when Wikipedia fetch fails
EXPLORE_TICKERS = [
    # Mega-cap tech
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AVGO", "ORCL", "AMD",
    # Financials
    "JPM", "BAC", "GS", "MS", "V", "MA", "BRK-B", "AXP", "BLK", "C",
    # Healthcare
    "JNJ", "UNH", "LLY", "ABBV", "PFE", "MRK", "TMO", "ABT", "AMGN", "GILD",
    # Consumer
    "WMT", "COST", "HD", "PG", "KO", "PEP", "MCD", "NKE", "SBUX", "TGT",
    # Energy
    "XOM", "CVX", "COP", "SLB", "OXY",
    # Other tech / growth
    "NFLX", "CRM", "ADBE", "INTC", "QCOM", "TXN", "IBM", "PYPL", "UBER", "COIN",
    # ETFs
    "SPY", "QQQ", "IWM",
]

TICKER_NAMES = {
    "AAPL": "Apple", "MSFT": "Microsoft", "GOOGL": "Alphabet", "AMZN": "Amazon",
    "NVDA": "NVIDIA", "META": "Meta", "TSLA": "Tesla", "AVGO": "Broadcom",
    "ORCL": "Oracle", "AMD": "AMD", "JPM": "JPMorgan", "BAC": "Bank of America",
    "GS": "Goldman Sachs", "MS": "Morgan Stanley", "V": "Visa", "MA": "Mastercard",
    "BRK-B": "Berkshire B", "AXP": "Amex", "BLK": "BlackRock", "C": "Citigroup",
    "JNJ": "J&J", "UNH": "UnitedHealth", "LLY": "Eli Lilly", "ABBV": "AbbVie",
    "PFE": "Pfizer", "MRK": "Merck", "TMO": "Thermo Fisher", "ABT": "Abbott",
    "AMGN": "Amgen", "GILD": "Gilead", "WMT": "Walmart", "COST": "Costco",
    "HD": "Home Depot", "PG": "P&G", "KO": "Coca-Cola", "PEP": "PepsiCo",
    "MCD": "McDonald's", "NKE": "Nike", "SBUX": "Starbucks", "TGT": "Target",
    "XOM": "ExxonMobil", "CVX": "Chevron", "COP": "ConocoPhillips",
    "SLB": "Schlumberger", "OXY": "Occidental", "NFLX": "Netflix",
    "CRM": "Salesforce", "ADBE": "Adobe", "INTC": "Intel", "QCOM": "Qualcomm",
    "TXN": "Texas Instruments", "IBM": "IBM", "PYPL": "PayPal", "UBER": "Uber",
    "COIN": "Coinbase", "SPY": "S&P 500 ETF", "QQQ": "Nasdaq 100 ETF",
    "IWM": "Russell 2000 ETF",
}


def _load_cache():
    """Return today's cached results, or None if stale/missing."""
    try:
        with open(_CACHE_PATH, encoding="utf-8") as f:
            data = json.load(f)
        if data.get("date") == str(_date.today()):
            return data.get("results")
    except Exception:
        pass
    return None


def _save_cache(results):
    try:
        os.makedirs(os.path.dirname(_CACHE_PATH), exist_ok=True)
        with open(_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump({"date": str(_date.today()), "results": results}, f)
    except Exception:
        pass


def _fetch_sp500_tickers():
    """Return (symbols, names_dict) from Wikipedia. Falls back to curated list on any error."""
    try:
        import pandas as pd
        import requests
        resp = requests.get(
            "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
            headers={"User-Agent": "Mozilla/5.0 (compatible; stock-app/1.0)"},
            timeout=10,
        )
        resp.raise_for_status()
        from io import StringIO
        tables = pd.read_html(StringIO(resp.text))
        df = tables[0]
        symbols = [s.replace(".", "-") for s in df["Symbol"].tolist()]
        names = dict(zip(symbols, df["Security"].tolist()))
        print(f"[Explore] S&P 500 fetch OK — {len(symbols)} tickers from Wikipedia")
        return symbols, names
    except Exception as e:
        print(f"[Explore] S&P 500 fetch FAILED ({e}) — falling back to curated list ({len(EXPLORE_TICKERS)} tickers)")
        return list(EXPLORE_TICKERS), dict(TICKER_NAMES)


class ExploreWorker(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, force=False):
        super().__init__()
        self._force = force

    def run(self):
        try:
            if not self._force:
                cached = _load_cache()
                if cached is not None:
                    print(f"[Explore] Cache hit — serving {len(cached)} stocks from today's cache")
                    self.finished.emit(cached)
                    return
                print("[Explore] Cache miss — fetching fresh data")

            import yfinance as yf

            self.progress.emit("Fetching S&P 500 ticker list...")
            tickers, ticker_names = _fetch_sp500_tickers()

            self.progress.emit(f"Downloading data for {len(tickers)} stocks...")
            data = yf.download(tickers, period="5d", progress=False, auto_adjust=True)

            results = []
            for symbol in tickers:
                try:
                    close = data["Close"][symbol].dropna()
                    volume = data["Volume"][symbol].dropna()
                    if len(close) < 2:
                        continue
                    today_close = float(close.iloc[-1])
                    prev_close = float(close.iloc[-2])
                    vol = float(volume.iloc[-1]) if not volume.empty else 0
                    change_pct = (today_close - prev_close) / prev_close * 100
                    results.append({
                        "symbol": symbol,
                        "name": ticker_names.get(symbol, symbol),
                        "price": today_close,
                        "change_pct": change_pct,
                        "volume": vol,
                    })
                except Exception:
                    continue

            _save_cache(results)
            print(f"[Explore] Download complete — {len(results)} stocks processed and cached")
            self.finished.emit(results)

        except Exception as e:
            print(f"[Explore] Worker error: {e}")
            self.error.emit(str(e))
