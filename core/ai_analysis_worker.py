import json
import os

import requests
import pandas as pd
from PyQt6.QtCore import QThread, pyqtSignal


class AIAnalysisWorker(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    status = pyqtSignal(str)

    def __init__(self, symbol, name, df):
        super().__init__()
        self.symbol = symbol
        self.name = name
        self.df = df.copy()

    def run(self):
        try:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                self.error.emit(
                    "ANTHROPIC_API_KEY is not set.\n\n"
                    "Add it to your .env file:\n  ANTHROPIC_API_KEY=sk-ant-..."
                )
                return

            self.status.emit("Fetching Senate trading data...")
            senate_summary = self._get_senate_trades()

            self.status.emit("Preparing market data...")
            price_summary = self._get_price_summary()

            self.status.emit("Running AI analysis...")
            result = self._call_claude(api_key, senate_summary, price_summary)
            result["price_summary"] = price_summary
            result["senate_summary"] = senate_summary
            self.finished.emit(result)

        except Exception as e:
            self.error.emit(str(e))

    def _get_senate_trades(self):
        try:
            url = f"https://senatestockwatcher.com/api/transactions?symbol={self.symbol}"
            resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code != 200:
                return None
            data = resp.json()
            if not data:
                return None
            lines = []
            for t in data[:15]:
                senator = t.get("senator") or t.get("name") or "Unknown"
                trade_type = t.get("type") or t.get("transaction_type") or "Unknown"
                date = t.get("transaction_date") or t.get("date") or "Unknown date"
                amount = t.get("amount") or "Unknown amount"
                lines.append(f"- {senator}: {trade_type} on {date} (amount: {amount})")
            return "\n".join(lines) if lines else None
        except Exception:
            return None

    def _get_price_summary(self):
        df = self.df.reset_index()
        recent = df.tail(30)
        start_price = float(recent["Close"].iloc[0])
        end_price = float(recent["Close"].iloc[-1])
        pct_change = ((end_price - start_price) / start_price) * 100
        high = float(recent["Close"].max())
        low = float(recent["Close"].min())
        summary = (
            f"Current price: ${end_price:.2f}\n"
            f"30-day change: {pct_change:+.2f}%\n"
            f"30-day high: ${high:.2f}\n"
            f"30-day low: ${low:.2f}"
        )
        if "Volume" in recent.columns:
            summary += f"\nAvg daily volume (30d): {float(recent['Volume'].mean()):,.0f}"
        return summary

    def _call_claude(self, api_key, senate_summary, price_summary):
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        senate_section = (
            f"Recent U.S. Senate member trades for {self.symbol}:\n{senate_summary}"
            if senate_summary
            else f"No Senate trading data was available for {self.symbol}."
        )

        prompt = f"""You are a financial analyst providing a short-term stock outlook.

Stock: {self.symbol} ({self.name})

Recent price data (last 30 days):
{price_summary}

{senate_section}

Using this data plus your knowledge of this company, recent news, industry trends, and macroeconomic conditions:

1. Give an integer score from -10 to 10 on the stock's 30-day outlook. Negative = bearish, positive = bullish, 0 = neutral.
2. Give a 1-2 sentence summary explaining the single most important reason the score landed where it did.
3. Give exactly 3 to 5 pros (reasons the stock may rise).
4. Give exactly 3 to 5 cons (reasons the stock may fall).

Be specific — reference real factors such as products, earnings, sector trends, or Senate activity if relevant. Avoid generic platitudes.

Respond ONLY with a JSON object in this exact format with no surrounding text:
{{
  "score": <integer -10 to 10>,
  "summary": "<1-2 sentences on the key driver>",
  "pros": ["...", "...", "..."],
  "cons": ["...", "...", "..."]
}}"""

        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )

        text = message.content[0].text.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

        return json.loads(text)
