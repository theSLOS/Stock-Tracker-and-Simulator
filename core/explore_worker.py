from PyQt6.QtCore import QThread, pyqtSignal

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


class ExploreWorker(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def run(self):
        try:
            import yfinance as yf

            self.progress.emit("Fetching market data...")
            data = yf.download(EXPLORE_TICKERS, period="5d", progress=False, auto_adjust=True)

            results = []
            for symbol in EXPLORE_TICKERS:
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
                        "name": TICKER_NAMES.get(symbol, symbol),
                        "price": today_close,
                        "change_pct": change_pct,
                        "volume": vol,
                    })
                except Exception:
                    continue

            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))
