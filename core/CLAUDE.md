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

**`CacheManager` key methods:** `set_stock_data(StockPackage)`, `get_stock_data(symbol)`, `rename_stock(symbol, new_name)` (updates `name` field + saves), `delete_stock(symbol, csv_path)`, `set_portfolio` / `get_portfolio` / `clear_portfolio`, `set_ai_analysis` / `get_ai_analysis` / `is_ai_analysis_fresh`.

---

## User profile format (`Users/<username>/profile.json`)

```json
{
    "username": "user3",
    "password": "pbkdf2sha256:260000:<salt>:<hex-digest>",
    "email": "user@example.com",
    "phone": "555-1234",
    "preferences": {
        "theme": "dark",
        "default_stock": "AAPL"
    }
}
```

`email` and `phone` are optional. Profile files **are** committed to git. Cache files and CSVs are gitignored.

Passwords are hashed with PBKDF2-HMAC-SHA256 (260 000 iterations) via `hash_password()` in `user_manager.py`. Use `verify_password(stored, provided)` for all auth checks — never compare the stored string directly. The legacy plain-text path (`stored == provided`) is still handled as a fallback for any old profiles that pre-date the hash update.

---

## Gitignore highlights

```
*.csv               # Stock price data — downloaded fresh on each machine
Users/*/cache       # Per-user cache files — regenerated automatically
Users/explore_cache.json  # Shared daily explore cache — regenerated automatically
.env                # API keys
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

## ExploreWorker (`explore_worker.py`)

- Fetches the S&P 500 ticker list from Wikipedia using `requests` + `pandas.read_html(StringIO(...))` with a browser User-Agent (required — Wikipedia 403s the default urllib agent)
- Falls back to a hardcoded 58-ticker curated list (`EXPLORE_TICKERS` / `TICKER_NAMES`) on any fetch error
- Daily cache at `Users/explore_cache.json` — format: `{"date": "YYYY-MM-DD", "results": [...]}`. Cache is checked before any network call; a cache hit skips the download entirely
- `ExploreWorker(force=False)` — default, used by `start_background_load()` at login; respects cache
- `ExploreWorker(force=True)` — used by the manual Refresh button; always re-downloads and overwrites the cache
- Batch-downloads 5 days of price + volume data via a single `yf.download()` call; computes `change_pct` as day-over-day close change
- Emits `progress(str)` during each stage so the status label stays informative; emits `finished(list)` with the processed results

---

## SenateWorker (`senate_worker.py`)

Name kept for historical reasons — fetches corporate insider trades, not congressional.

- Fetches up to 20 recent SEC transactions via `finnhub.io/api/v1/stock/insider-transactions`
- Transaction codes: `P` Purchase, `S` Sale, `A` Award, `D` Disposition, `G` Gift, `F` Tax Withholding
- Failures handled silently; shows nothing if `FINNHUB_API_KEY` is absent
- Finnhub's congressional trading endpoint (`/api/v1/stock/congressional-trading`) requires a paid plan — free tier only covers corporate insider trades
