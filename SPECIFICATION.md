# MASTER ARCHITECTURE & SPECIFICATION: 24/7 ICT SCANNER & AI ANALYST

> **Instructions for Antigravity IDE:** Read this entire document first. Then execute Phases 1–9 (Section 9) sequentially. After each phase, run the tests/verification listed for that phase before moving on. Do not skip phases. Follow the "Implementation Notes" in Section 8 — they resolve known pitfalls.

---

## 1. Executive Summary & Core Objectives

* **System Purpose:** An automated, headless algorithmic trading scanner operating 24/7 on a cloud VPS across 10–15 selected Forex, Crypto, and Index pairs. It is an **alerting/analysis tool only** — it does NOT place trades.
* **Core Strategy:** Pure Inner Circle Trader (ICT) algorithmic concepts:
  * Liquidity Sweeps (BSL/SSL).
  * Market Structure Shifts (MSS) with displacement body candle closes.
  * Fair Value Gaps (FVG) and Order Blocks (OB).
  * Premium vs. Discount pricing (Equilibrium).
  * Time-based Session Killzones (London Open, New York AM).
* **AI Evaluation Layer:** Before dispatching an alert, detected setups are fed into an LLM (e.g., OpenAI GPT-4o or Claude Sonnet) to evaluate confluence, assign a probability score (1–100%), and write a technical thesis. Setups below a configurable threshold (default 75%) are discarded.
* **Alert Delivery:** Formatted alerts sent instantly to Telegram and Email.
* **Zero PC Dependency:** Packaged in Docker Compose with auto-restart policies to run indefinitely on a cheap Linux VPS (Ubuntu).
* **Control Center:** A lightweight FastAPI + Web Admin Panel to toggle pairs, adjust risk parameters, view logs, and trigger manual re-scans.

> **Note on the "probability score":** The LLM score is a subjective confluence rating, not a statistically validated win probability. Label it "Confluence Score" in the UI where possible and do not present it as a guaranteed or calibrated probability.

---

## 2. Directory Structure

```text
ict-trading-bot/
├── SPECIFICATION.md
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
├── README.md
├── config/
│   ├── __init__.py
│   ├── settings.py
│   └── pairs.json
├── core/
│   ├── __init__.py
│   ├── data_feed.py           # Multi-timeframe OHLCV fetcher (CCXT / TwelveData)
│   ├── scheduler.py           # 24/7 cron loop & session killzone timer
│   ├── ict/
│   │   ├── __init__.py
│   │   ├── fractals.py        # Swing High/Low calculations
│   │   ├── liquidity.py       # BSL / SSL pool sweep detection
│   │   ├── structure.py       # Market Structure Shift (MSS) + Displacement
│   │   ├── imbalance.py       # Fair Value Gap (FVG) detection & mitigation
│   │   └── engine.py          # ICT Confluence state machine
│   └── ai/
│       ├── __init__.py
│       ├── prompt_templates.py
│       └── evaluator.py       # LLM confluence reasoning & probability scoring
├── db/
│   ├── __init__.py
│   ├── database.py            # SQLite WAL / PostgreSQL async connection
│   └── models.py              # SQLAlchemy / SQLModel schema
├── notifications/
│   ├── __init__.py
│   ├── telegram_bot.py        # Async Telegram dispatcher
│   └── email_service.py       # SMTP / HTML email dispatcher
├── api/
│   ├── __init__.py
│   ├── main.py                # FastAPI entry point (starts scheduler in lifespan)
│   ├── routes.py              # Admin REST endpoints
│   └── static/                # Admin Panel UI (Tailwind + Alpine.js / HTML)
└── tests/
    ├── __init__.py
    ├── test_data.json
    └── test_ict_engine.py     # Deterministic backtest & logic verification
```

---

## 3. Algorithmic ICT Detection Logic

### 3.1 Multi-Timeframe Analysis Pipeline
* **Higher Timeframe (HTF - 4H / 1D):** Determines overall market bias and locates major Liquidity Pools (BSL/SSL).
* **Intermediate Timeframe (ITF - 1H / 15M):** Confirms structural trend and locates unmitigated Fair Value Gaps.
* **Lower Timeframe (LTF - 5M / 1M):** Pinpoints the precise entry trigger, Stop Loss (SL), and Take Profit (TP).

### 3.2 Detection Rules & Pseudocode

1. **Swing High / Swing Low (5-Bar Fractal):**
   * Swing High at index `i`: `High[i] > High[i-1] AND High[i] > High[i-2] AND High[i] > High[i+1] AND High[i] > High[i+2]`
   * Swing Low at index `i`: `Low[i] < Low[i-1] AND Low[i] < Low[i-2] AND Low[i] < Low[i+1] AND Low[i] < Low[i+2]`
   * A swing is only *confirmed* 2 candles after it forms. Never use unconfirmed swings (avoids repainting / lookahead bias).

2. **Liquidity Sweep (BSL / SSL):**
   * Bearish Sweep (BSL): Price wick exceeds a previous Swing High, but candle close is strictly below that Swing High.
   * Bullish Sweep (SSL): Price wick exceeds a previous Swing Low, but candle close is strictly above that Swing Low.
   * Additional liquidity references: Asian Range high/low, previous day high/low (PDH/PDL).

3. **Market Structure Shift (MSS):**
   * Must follow a liquidity sweep within `N` candles (configurable, default `N = 10`).
   * Requires a full candle **body close** above the most recent Swing High (Bullish MSS) or below the most recent Swing Low (Bearish MSS) with displacement (candle body size `>= 1.5 x` the 14-period Average True Range).

4. **Fair Value Gap (FVG):**
   * Bullish FVG: `Low[Candle 3] > High[Candle 1]`. Imbalance Zone: `[High[Candle 1], Low[Candle 3]]`.
   * Bearish FVG: `High[Candle 3] < Low[Candle 1]`. Imbalance Zone: `[High[Candle 3], Low[Candle 1]]`.
   * Unmitigated status remains valid until a subsequent candle wick touches the imbalance boundary.

5. **Order Block (OB):**
   * Bullish OB: the last down-close candle before the bullish displacement leg that caused the MSS.
   * Bearish OB: the last up-close candle before the bearish displacement leg that caused the MSS.
   * Used as an optional confluence factor alongside the FVG.

6. **Premium / Discount (Equilibrium):**
   * Define the dealing range from the swept swing to the MSS-confirming swing. Equilibrium = 50% of that range.
   * `BUY` entries should sit in Discount (below 50%); `SELL` entries should sit in Premium (above 50%).

7. **Session Killzones (UTC):**
   * London Open: `07:00 – 10:00 UTC`
   * New York AM: `12:00 – 15:00 UTC`
   * Asian Range (Reference): `00:00 – 06:00 UTC` (Used for liquidity reference; no execution triggers).
   * Crypto trades 24/7 but the same killzone filter applies for consistency (configurable flag per asset class).

8. **Trade Level Construction (defaults, all configurable):**
   * Entry: FVG midpoint (Consequent Encroachment) or OB open.
   * Stop Loss: beyond the swept liquidity level +/- small ATR buffer.
   * Take Profit: nearest opposing HTF liquidity pool.
   * Reject setups with `rr_ratio < MIN_RR` (default `2.0`).

---

## 4. Database Schema (SQLite with WAL or PostgreSQL)

Implement through SQLAlchemy / SQLModel ORM models. The SQL below is the reference schema.

```sql
-- Track configured watchlist pairs
CREATE TABLE pairs_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol VARCHAR(30) UNIQUE NOT NULL,       -- e.g., 'EUR/USD', 'BTC/USDT', 'NAS100'
    asset_class VARCHAR(15) NOT NULL,         -- 'forex', 'crypto', 'index'
    is_active BOOLEAN DEFAULT 1,
    timeframes VARCHAR(60) DEFAULT '1D,4H,15M,5M',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Store raw ICT signals identified by the engine
CREATE TABLE detected_setups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol VARCHAR(30) NOT NULL,
    session_name VARCHAR(30) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    direction VARCHAR(10) NOT NULL,          -- 'BUY' or 'SELL'
    sweep_level REAL NOT NULL,
    displacement_atr REAL NOT NULL,
    fvg_high REAL NOT NULL,
    fvg_low REAL NOT NULL,
    entry_price REAL NOT NULL,
    stop_loss REAL NOT NULL,
    take_profit REAL NOT NULL,
    rr_ratio REAL NOT NULL,
    dedupe_key VARCHAR(120) UNIQUE NOT NULL, -- symbol|direction|sweep_level|fvg bounds (prevents duplicate alerts)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Store LLM evaluations and probability output
CREATE TABLE ai_evaluations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    setup_id INTEGER NOT NULL REFERENCES detected_setups(id) ON DELETE CASCADE,
    probability_score INTEGER NOT NULL,      -- 1 to 100
    market_bias VARCHAR(20) NOT NULL,
    narrative_thesis TEXT NOT NULL,
    invalidation_rule TEXT NOT NULL,
    approved_for_alert BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Outbound notification logs
CREATE TABLE alert_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    setup_id INTEGER NOT NULL REFERENCES detected_setups(id),
    channel VARCHAR(20) NOT NULL,            -- 'TELEGRAM', 'EMAIL'
    status VARCHAR(20) NOT NULL,             -- 'SENT', 'FAILED'
    response_payload TEXT,
    dispatched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Heartbeat & error logging
CREATE TABLE system_health_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    component VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,             -- 'HEALTHY', 'DEGRADED', 'ERROR'
    message TEXT,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 5. AI Reasoning Agent Pipeline

### 5.1 LLM System & User Prompt

```text
[SYSTEM]
You are a Lead Quantitative ICT Analyst. Your job is to strictly evaluate algorithmic trading setups against institutional order flow principles. Be objective and reject weak signals. Output valid JSON only, with no markdown fences and no extra text.

[USER]
Evaluate the following detected trade setup:
- Asset: {symbol}
- Killzone: {session_name}
- Multi-Timeframe Context: 4H Bias={htf_bias}, 15M Trend={itf_trend}
- Setup Direction: {direction}
- Liquidity Pool Swept: {sweep_level}
- FVG Entry Zone: [{fvg_low} - {fvg_high}]
- Trade Levels: Entry={entry_price}, SL={stop_loss}, TP={take_profit} (R:R = 1:{rr_ratio})

Respond in the following JSON format:
{
  "probability_score": <int 1-100>,
  "approved": <bool: true if score >= {min_threshold}>,
  "market_bias": "<Bullish | Bearish | Neutral>",
  "thesis": "<Concise 3-sentence technical justification of why this setup has high probability>",
  "invalidation": "<Exact price action or event that cancels the trade thesis>",
  "confluence_checklist": [
    "<Factor 1>",
    "<Factor 2>",
    "<Factor 3>"
  ]
}
```

### 5.2 Evaluator Behavior
* Use the provider's JSON / structured-output mode where available; always validate the response with a Pydantic model.
* Do **not** trust the model's `approved` field. Compute approval in code: `approved = probability_score >= MIN_PROBABILITY_THRESHOLD`.
* On malformed JSON: retry once, then log to `system_health_logs` and skip the setup (never send an alert on a failed evaluation).
* Set a request timeout (e.g., 30s) and low temperature (e.g., 0.2).
* Support provider switching via env (`AI_PROVIDER=openai|anthropic|openrouter`).

---

## 6. Notification Templates

### 6.1 Telegram Alert Format
```text
🚨 ICT SETUP DETECTED: {symbol}
━━━━━━━━━━━━━━━━━━━━━━
⚡ Direction: {direction} | Killzone: {session_name}
📊 Confluence Probability: {probability_score}%

🎯 Execution Levels:
• Entry: {entry_price}
• Stop Loss: {stop_loss}
• Take Profit: {take_profit}
• Risk/Reward: 1:{rr_ratio}

🧠 AI Technical Rationale:
{thesis}

⚠️ Invalidation:
{invalidation}

🕒 Time: {timestamp_utc} UTC
━━━━━━━━━━━━━━━━━━━━━━
```
*Escape special characters if using MarkdownV2, or send with `parse_mode=None`/HTML to avoid formatting errors.*

### 6.2 HTML Email Alert Format
```html
<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; border: 1px solid #e0e0e0; border-radius: 8px; padding: 20px; background-color: #fafafa;">
  <div style="background-color: #111827; color: #ffffff; padding: 12px 16px; border-radius: 6px;">
    <h2 style="margin: 0; font-size: 18px;">ICT Trade Alert: {{symbol}} ({{direction}})</h2>
  </div>
  <div style="margin: 20px 0; background-color: #ffffff; padding: 16px; border-radius: 6px; border: 1px solid #eee;">
    <p><strong>Session:</strong> {{session_name}}</p>
    <p><strong>AI Probability Score:</strong> <span style="font-size: 18px; color: #10b981; font-weight: bold;">{{probability_score}}%</span></p>
    <hr style="border: 0; border-top: 1px solid #f0f0f0;" />
    <table style="width: 100%; font-size: 14px; text-align: left;">
      <tr><td><strong>Entry:</strong> {{entry_price}}</td><td><strong>SL:</strong> {{stop_loss}}</td></tr>
      <tr><td><strong>TP:</strong> {{take_profit}}</td><td><strong>R:R:</strong> 1:{{rr_ratio}}</td></tr>
    </table>
  </div>
  <div style="background-color: #ffffff; padding: 16px; border-radius: 6px; border: 1px solid #eee;">
    <h4 style="margin-top: 0;">AI Technical Thesis:</h4>
    <p style="font-size: 14px; line-height: 1.5; color: #374151;">{{thesis}}</p>
    <h4 style="margin-top: 10px; color: #b91c1c;">Invalidation Condition:</h4>
    <p style="font-size: 14px; color: #b91c1c;">{{invalidation}}</p>
  </div>
  <p style="font-size: 11px; color: #9ca3af; text-align: center; margin-top: 20px;">Automated 24/7 Scanner Cloud Node • Generated at {{timestamp_utc}} UTC • Not financial advice</p>
</div>
```
*Render with Jinja2 (autoescape ON).*

---

## 7. Deployment Files (24/7 Headless Cloud VPS)

### 7.1 `Dockerfile`
```dockerfile
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# DB init runs first; the scheduler is started INSIDE the FastAPI lifespan (see Section 8).
CMD ["sh", "-c", "python -m db.database && uvicorn api.main:app --host 0.0.0.0 --port 8000"]
```
*`db/database.py` must include an `if __name__ == "__main__":` block that runs `asyncio.run(init_db())` (create tables + enable WAL).*

### 7.2 `docker-compose.yml`
```yaml
services:
  ict-scanner:
    build: .
    container_name: ict_trading_bot
    restart: always
    ports:
      - "8000:8000"
    environment:
      - PYTHONUNBUFFERED=1
    env_file:
      - .env
    volumes:
      - ./data:/app/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### 7.3 `.env.example`
```env
# Runtime
ENVIRONMENT=production
PORT=8000
DATABASE_URL=sqlite+aiosqlite:///data/trading_bot.db

# Admin panel security (REQUIRED - panel is exposed on the internet)
ADMIN_API_KEY=change_me_to_a_long_random_string

# Market Data APIs
CRYPTO_EXCHANGE=binance
TWELVE_DATA_API_KEY=your_twelve_data_key_here
OANDA_API_KEY=your_oanda_key_here

# AI Engine
AI_PROVIDER=openai
OPENAI_API_KEY=your_openai_or_openrouter_api_key
ANTHROPIC_API_KEY=your_anthropic_key_here
AI_MODEL=gpt-4o
MIN_PROBABILITY_THRESHOLD=75

# Strategy parameters
MIN_RR=2.0
MSS_LOOKBACK_CANDLES=10
DISPLACEMENT_ATR_MULTIPLIER=1.5
SCAN_INTERVAL_SECONDS=300

# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Email Notifications (SMTP / Resend)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASS=your_app_password
ALERT_RECIPIENT_EMAIL=your_email@gmail.com
```

### 7.4 `requirements.txt` (starting point)
```text
fastapi
uvicorn[standard]
pydantic
pydantic-settings
sqlalchemy[asyncio]
aiosqlite
asyncpg
ccxt
httpx
pandas
numpy
openai
anthropic
python-telegram-bot
aiosmtplib
jinja2
python-dotenv
pytest
pytest-asyncio
```
*Pin exact versions after the first successful build.*

### 7.5 VPS Deployment Commands
```bash
# Update system & install Docker on Ubuntu VPS
sudo apt update && sudo apt install -y git docker.io docker-compose-v2

# Clone or transfer your project into the VPS
cd /root/ict-trading-bot

# Set up environment variables
cp .env.example .env
nano .env

# Build and start container in the background
sudo docker compose up -d --build

# Inspect 24/7 logs
sudo docker compose logs -f
```
*If `docker-compose-v2` isn't available on your Ubuntu version, use `docker-compose` (with a hyphen) instead.*

---

## 8. Implementation Notes (Resolves Known Pitfalls)

1. **Single process:** The scheduler runs as an `asyncio` background task started in FastAPI's `lifespan` handler in `api/main.py` (and cancelled cleanly on shutdown). Do not use a second container or a separate process.
2. **Admin security:** All `/api/*` routes except `/api/health` require the header `X-API-Key: <ADMIN_API_KEY>`. The dashboard prompts for the key and stores it in memory/sessionStorage. Recommend placing behind Nginx/Caddy with HTTPS.
3. **No lookahead / repainting:** The engine must only use **closed** candles. Drop the currently forming candle from every fetch.
4. **Deduplication:** Compute `dedupe_key` for each setup; skip insertion/alerting if it already exists (unique constraint). Also add a per-symbol cooldown (default 60 min).
5. **Data sources:**
   * Crypto: `ccxt` (public OHLCV endpoints, no key required for Binance spot data).
   * Forex / Gold / Indices (EUR/USD, XAU/USD, NAS100, US30): TwelveData or OANDA REST. Maintain a symbol-mapping dict per provider in `config/pairs.json`.
   * Respect provider rate limits: cache candles per `(symbol, timeframe)` and fetch only new candles incrementally.
6. **Resilience:** Wrap each pair's scan in try/except so one failing symbol never stops the loop. Use exponential backoff on network errors. Write `HEALTHY/DEGRADED/ERROR` rows to `system_health_logs` and expose the latest state at `/api/health`.
7. **Cost control:** Call the LLM only for setups that pass all deterministic ICT checks, and never twice for the same `dedupe_key`.
8. **Timezone:** All timestamps are UTC and timezone-aware (`datetime.now(timezone.utc)`).
9. **SQLite WAL:** On connection, execute `PRAGMA journal_mode=WAL;` and `PRAGMA busy_timeout=5000;`.
10. **Secrets:** Never log API keys or tokens. `.env` must be in `.gitignore`.
11. **Disclaimer:** Alerts are informational and not financial advice. The system does not execute orders.

---

## 9. Step-by-Step Implementation Checklist for Antigravity

Execute the following phases in sequence. Verify each phase before continuing.

- [ ] **Phase 1: Project Scaffolding & Configuration**
  - Generate full directory tree, `requirements.txt`, `.env.example`, `.gitignore`, and `config/settings.py` (Pydantic `BaseSettings`).
  - Configure initial 10–15 pairs in `config/pairs.json` (e.g., EUR/USD, GBP/USD, USD/JPY, AUD/USD, XAU/USD, BTC/USDT, ETH/USDT, SOL/USDT, NAS100, US30), including per-provider symbol mappings.
  - *Verify:* `python -c "from config.settings import settings"` succeeds.

- [ ] **Phase 2: Database Layer**
  - Implement async SQLite/PostgreSQL initialization via SQLAlchemy in `db/database.py` and models in `db/models.py`.
  - Enable WAL mode for high-concurrency read/writes without database locking.
  - Seed `pairs_config` from `pairs.json` on first run.
  - *Verify:* `python -m db.database` creates all tables.

- [ ] **Phase 3: Market Data Ingestion Pipeline**
  - Build `core/data_feed.py` using `ccxt` for Crypto and TwelveData / OANDA REST API for Forex & Indices.
  - Implement caching and multi-timeframe candle sync (1D, 4H, 15M, 5M).
  - Return pandas DataFrames with columns `timestamp, open, high, low, close, volume`, closed candles only.

- [ ] **Phase 4: ICT Technical Detection Engine**
  - Implement `core/ict/fractals.py` (5-candle swing detection).
  - Implement `core/ict/liquidity.py` (BSL/SSL sweep identification).
  - Implement `core/ict/structure.py` (MSS with displacement ATR check).
  - Implement `core/ict/imbalance.py` (FVG identification and mitigation).
  - Unify into `core/ict/engine.py` to trigger setups only during London and New York Killzones; include OB and Premium/Discount checks and MIN_RR filter.
  - Write test coverage in `tests/test_ict_engine.py` with mock candle data (bullish case, bearish case, no-sweep case, wick-only-no-MSS case, outside-killzone case).
  - *Verify:* `pytest tests/` passes.

- [ ] **Phase 5: AI Confluence & Probability Evaluator**
  - Build `core/ai/evaluator.py` to query OpenAI / Claude API using structured JSON output (see Section 5.2).
  - Apply logic: if `probability_score < MIN_PROBABILITY_THRESHOLD`, mark setup as unapproved and log reason.
  - Add a mocked-LLM unit test.

- [ ] **Phase 6: Multi-Channel Dispatcher**
  - Implement `notifications/telegram_bot.py` using `python-telegram-bot` to send formatted alerts (Section 6.1).
  - Implement `notifications/email_service.py` to dispatch HTML emails (Section 6.2) via `aiosmtplib`.
  - Log every attempt (SENT/FAILED) to `alert_logs`; one channel failing must not block the other.

- [ ] **Phase 7: Background Scheduler & 24/7 Loop**
  - Implement `core/scheduler.py` using `asyncio` loop running every `SCAN_INTERVAL_SECONDS` (default 300s; align to candle closes).
  - Pipeline: Fetch candles -> Run ICT Engine -> Dedupe -> Run AI Evaluator -> Send Alerts -> Persist to DB.
  - Write a heartbeat to `system_health_logs` each cycle.

- [ ] **Phase 8: FastAPI Backend & Web Admin Dashboard**
  - Implement REST routes in `api/routes.py` (all but health require `X-API-Key`):
    - `GET /api/pairs` & `POST /api/pairs/toggle`
    - `GET /api/setups` (history of detected setups & AI probability)
    - `GET /api/settings` & `POST /api/settings` (threshold, MIN_RR, scan interval)
    - `GET /api/logs` (recent health + alert logs)
    - `GET /api/health`
    - `POST /api/scan/manual` (force trigger scan)
  - Serve a responsive dashboard at `GET /` (Tailwind + Alpine.js) showing active pairs with toggles, live setups/alerts, and system health status.

- [ ] **Phase 9: Dockerization & End-to-End Verification**
  - Validate container build via `docker compose up --build`.
  - Run end-to-end integration test with mock candle data and a mocked LLM to verify Telegram and Email alerts fire successfully.
  - Confirm container auto-restarts (`docker kill` then check it comes back) and the healthcheck reports healthy.
  - Write `README.md` with setup, env var reference, and VPS deployment steps.
