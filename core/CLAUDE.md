# core — Business Logic Reference

---

## Cache format (`Users/<username>/cache`)

```json
{
    "AAPL": {
        "name": "Apple",
        "symbol": "AAPL",
        "dfpath": "AAPL.csv",
        "lastUpdate": "2026-05-18T14:01:37.540076",
        "ai_analysis": {
            "timestamp": "2026-05-25T10:30:00.000000",
            "score": 7,
            "summary": "Apple's iPhone supercycle narrative...",
            "pros": ["Strong earnings growth", "..."],
            "cons": ["High valuation", "..."]
        },
        "portfolio": {
            "shares": 10,
            "cost_per_share": 182.50,
            "purchase_date": "2025-01-15",
            "sell_target": 220.00
        }
    }
}
```

`dfpath` is **filename only** — always join with `csv_path` to get the full path. `ai_analysis` and `portfolio` are optional keys; absent until the user runs that feature. `sell_target` inside `portfolio` is also optional.

---

## User profile format (`Users/<username>/profile.json`)

```json
{
    "username": "user3",
    "password": "password",
    "email": "user@example.com",
    "phone": "555-1234",
    "preferences": {
        "theme": "dark",
        "default_stock": "AAPL"
    }
}
```

`email` and `phone` are optional. Profile files **are** committed to git. Cache files and CSVs are gitignored.

---

## Gitignore highlights

```
*.csv          # Stock price data — downloaded fresh on each machine
Users/*/cache  # Per-user cache files — regenerated automatically
.env           # API keys
```

Profile JSONs and `pyrightconfig.json` are committed.

---

## PredictionWorker (`prediction_worker.py`)

- Trains on last 2 years of data (`cutoff = max_date - 730 days`)
- `changepoint_prior_scale=0.05`, `changepoint_range=0.80` — tuned to reduce upward bias; 0.80 prevents over-anchoring to recent momentum
- Returns `(predicted_price, low, high)` for 30 days ahead
- `prophet` import deferred to `run()` so startup is unaffected

---

## AIAnalysisWorker (`ai_analysis_worker.py`)

- Fetches up to 15 recent insider trades from Finnhub (`FINNHUB_API_KEY`)
- Builds a 30-day price summary (current price, change %, high, low, avg volume)
- Calls Claude (`claude-sonnet-4-6`) with a structured prompt; expects JSON: `{score, summary, pros, cons}`
- Score: -10 (strongly bearish) to +10 (strongly bullish). `summary` is 1-2 sentences.
- Result cached per-stock per-user for 24 hours; API only called when stale or absent
- `anthropic` import deferred to `run()`

---

## SenateWorker (`senate_worker.py`)

Name kept for historical reasons — fetches corporate insider trades, not congressional.

- Fetches up to 20 recent SEC transactions via `finnhub.io/api/v1/stock/insider-transactions`
- Transaction codes: `P` Purchase, `S` Sale, `A` Award, `D` Disposition, `G` Gift, `F` Tax Withholding
- Failures handled silently; shows nothing if `FINNHUB_API_KEY` is absent
- Finnhub's congressional trading endpoint (`/api/v1/stock/congressional-trading`) requires a paid plan — free tier only covers corporate insider trades
