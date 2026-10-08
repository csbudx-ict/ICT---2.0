# SPECIFICATION V2 — 24/7 LIVE ICT SCANNER, CHART-ANNOTATING AI ANALYST & TELEGRAM TRADE DESK

> **Instructions for Antigravity IDE (READ FIRST):**
> 1. This document **replaces** `SPECIFICATION.md` (V1). Where they conflict, V2 wins.
> 2. Build as a **professional software engineer** would: Git from commit #1, `src/` layout, typed code, tests, linting, CI, migrations, structured logging, Docker multi-stage, documentation. Section 3 is mandatory, not optional.
> 3. Execute the phases in Section 14 in order. Do not start a phase until the previous phase's **Definition of Done (DoD)** passes.
> 4. The Telegram bot is **already created**. The owner will put `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in `.env`. Never hardcode or print them.

---

## 1. What the Owner Wants (Non-Negotiable Requirements)

| # | Requirement | How V2 delivers it |
|---|-------------|--------------------|
| R1 | Analyze **live market data 24/7**, always | Event-driven streaming data layer (WebSockets + tick→candle builder), auto-reconnect, gap backfill, staleness watchdog, Docker `restart: always` (Section 5) |
| R2 | System **marks every tool on the chart**: zones, boxes, TP, SL, lines, long/short position, Fib, etc. | Server-side **chart renderer** that draws all ICT objects as annotated PNGs (Section 7) |
| R3 | Send the entry to Telegram **with a screenshot** | Annotated chart image(s) sent via Telegram `sendPhoto` / `sendMediaGroup` (Section 9) |
| R4 | Include **example, probability, why take this entry, reason, everything** | Full trade-desk message: levels, probability, thesis, confluence checklist, invalidation, position-size example, key levels, MTF bias (Section 9) |
| R5 | Files organized **like a professional developer** | Professional repo standards (Section 3) |
| R6 | Run on a cheap VPS, no PC needed | Docker Compose, headless chart rendering (matplotlib `Agg`), no GUI/browser (Section 12) |

**Important design decision — screenshots:** The bot does **not** screenshot TradingView (that needs a logged-in browser, breaks often, and violates TradingView terms for automation). Instead, the bot **draws its own TradingView-style chart** from the live candle data using matplotlib. It is faster, 100% headless, fully reliable on a VPS, and every ICT object is drawn exactly where the engine detected it.

---

## 2. System Overview

```text
 LIVE DATA                     ANALYSIS                       OUTPUT
┌─────────────────┐   ┌───────────────────────────┐   ┌──────────────────────────┐
│ Crypto WebSocket│   │ Candle Store (ring buffers)│   │ Chart Renderer (PNG)     │
│ (ccxt.pro)      │──▶│ 1D / 4H / 1H / 15M / 5M    │   │  zones, boxes, fib, TP/SL│
│ Forex/Index     │   │            │               │   │  lines, long/short tool  │
│ (TwelveData WS /│   │   candle-close event       │   └────────────┬─────────────┘
│  OANDA stream)  │   │            ▼               │                │
└─────────────────┘   │ ICT Engine (deterministic) │   ┌────────────▼─────────────┐
                      │ sweep→MSS→FVG/OB→fib→levels│──▶│ AI Analyst (LLM) + Score │
                      │            │               │   └────────────┬─────────────┘
                      │   Setup passes rules?      │                │ approved?
                      └────────────┬───────────────┘   ┌────────────▼─────────────┐
                                   │                   │ Telegram: chart + message│
                                   ▼                   │ Email (optional)         │
                         ┌───────────────────┐         └────────────┬─────────────┘
                         │ DB (setups, evals,│◀─────────────────────┘
                         │ alerts, outcomes) │──▶ Outcome Tracker (TP/SL hit) → real win-rate stats
                         └───────────────────┘
```

**Event-driven, not slow polling:** analysis for a symbol runs **the moment a candle closes** on 5M/15M (plus a light 30-second tick for open-setup monitoring), so alerts arrive within seconds of the trigger candle closing.

---

## 3. Professional Engineering Standards (MANDATORY)

Antigravity must set the project up exactly as a senior developer would.

### 3.1 Repository Layout

```text
ict-scanner/
├── AGENTS.md                       # Rules for AI coding agents (content in 3.4)
├── README.md                       # Overview, quick start, screenshots, architecture link
├── SPECIFICATION.md                # V1 (kept for history)
├── SPECIFICATION_V2.md             # This file
├── CHANGELOG.md                    # Keep-a-Changelog format
├── CONTRIBUTING.md                 # Branching, commit style, how to run checks
├── LICENSE
├── pyproject.toml                  # Single source of truth: deps, ruff, mypy, pytest, coverage
├── Makefile                        # make install | lint | type | test | run | docker-up | sample-chart
├── .env.example
├── .gitignore
├── .dockerignore
├── .editorconfig
├── .pre-commit-config.yaml
├── .github/
│   └── workflows/ci.yml            # lint + type-check + tests on every push/PR
├── Dockerfile                      # multi-stage, non-root user
├── docker-compose.yml
├── alembic.ini
├── migrations/                     # Alembic versions (no manual DDL in production)
├── docs/
│   ├── architecture.md
│   ├── strategy.md                 # ICT rules in plain language + diagrams
│   ├── charting.md                 # Every drawn object, colors, meaning
│   ├── deployment.md               # VPS guide
│   └── runbook.md                  # What to do when X breaks
├── scripts/
│   ├── send_test_alert.py          # Sends a fake setup + chart to Telegram (verifies bot)
│   ├── render_sample_chart.py      # Renders a chart from fixture data to ./out/
│   └── backfill_history.py
├── data/                           # gitignored runtime data (SQLite, chart cache)
├── src/
│   └── ict_scanner/
│       ├── __init__.py
│       ├── __main__.py             # `python -m ict_scanner`
│       ├── app.py                  # Composition root: wires everything (dependency injection)
│       ├── config/
│       │   ├── settings.py         # pydantic-settings
│       │   └── pairs.yaml          # watchlist + provider symbol maps
│       ├── domain/                 # Pure data types, NO I/O
│       │   ├── enums.py            # Direction, Timeframe, AssetClass, Session
│       │   └── models.py           # Candle, Swing, LiquidityPool, Sweep, MSS, FVG, OrderBlock,
│       │                           #   FibLevels, DealingRange, TradePlan, Setup
│       ├── data/
│       │   ├── base.py             # MarketDataProvider protocol
│       │   ├── crypto_ccxt.py      # ccxt.pro WebSocket streams
│       │   ├── forex_twelvedata.py # TwelveData WebSocket + REST backfill
│       │   ├── forex_oanda.py      # OANDA v20 streaming (alternative)
│       │   ├── candle_builder.py   # ticks → candles, multi-timeframe aggregation
│       │   ├── candle_store.py     # in-memory ring buffers per (symbol, timeframe)
│       │   └── watchdog.py         # staleness + reconnect supervision
│       ├── ict/
│       │   ├── fractals.py
│       │   ├── liquidity.py        # BSL/SSL, PDH/PDL, Asian range, equal highs/lows
│       │   ├── structure.py        # MSS / BOS + displacement
│       │   ├── imbalance.py        # FVG detection + mitigation tracking
│       │   ├── order_blocks.py
│       │   ├── premium_discount.py # dealing range, equilibrium
│       │   ├── fibonacci.py        # retracement/OTE/extension levels
│       │   ├── killzones.py
│       │   ├── levels.py           # entry / SL / TP1 / TP2 construction
│       │   ├── scoring.py          # rule-based confluence score
│       │   └── engine.py           # state machine producing Setup objects
│       ├── charting/
│       │   ├── theme.py            # dark theme, colors, fonts
│       │   ├── primitives.py       # draw_box, draw_hline, draw_label, draw_arrow, draw_position_tool
│       │   ├── layers.py           # one function per ICT object type (see Section 7.3)
│       │   └── renderer.py         # compose layers → PNG bytes
│       ├── ai/
│       │   ├── prompts.py
│       │   ├── schemas.py          # Pydantic models for LLM JSON
│       │   ├── providers.py        # OpenAI / Anthropic / OpenRouter adapters
│       │   └── analyst.py
│       ├── notifications/
│       │   ├── formatter.py        # builds the trade-desk message (Section 9)
│       │   ├── telegram.py         # sendPhoto/sendMediaGroup/sendMessage + inline buttons
│       │   └── email.py
│       ├── tracking/
│       │   ├── outcome_tracker.py  # watches open setups: TP1/TP2/SL hit, expiry
│       │   └── stats.py            # win rate, avg R, per-symbol/per-session stats
│       ├── orchestrator/
│       │   ├── pipeline.py         # candle-close → engine → AI → chart → alert → persist
│       │   └── scheduler.py        # supervised asyncio tasks
│       ├── db/
│       │   ├── session.py
│       │   ├── models.py           # SQLAlchemy ORM
│       │   └── repositories.py     # data-access layer (no SQL in business logic)
│       ├── api/
│       │   ├── main.py             # FastAPI + lifespan (starts the orchestrator)
│       │   ├── deps.py             # auth (X-API-Key)
│       │   ├── routes/             # pairs.py, setups.py, health.py, settings.py, charts.py, stats.py
│       │   └── static/             # dashboard (Tailwind + Alpine.js)
│       └── observability/
│           ├── logging.py          # structured JSON logs (structlog)
│           └── metrics.py          # counters: candles_received, setups_found, alerts_sent
└── tests/
    ├── unit/                       # ict/, charting/, notifications/, data/
    ├── integration/                # pipeline end-to-end with fake provider + fake Telegram
    ├── fixtures/                   # OHLCV CSV/JSON with known sweeps/MSS/FVGs
    └── golden/                     # reference chart PNGs (image-diff regression tests)
```

### 3.2 Tooling & Quality Gates
* **Python 3.11+**, `pyproject.toml` (PEP 621). Dependency manager: `uv` or `pip-tools`; lock versions.
* **Ruff** (lint + format), **mypy** (strict on `domain/`, `ict/`, `charting/`), **pytest** + `pytest-asyncio` + `pytest-cov`.
* **pre-commit** hooks: ruff, ruff-format, mypy, trailing-whitespace, detect-private-key, check-added-large-files.
* **Coverage gate:** ≥ 85% on `ict/`, ≥ 75% on `charting/` and `notifications/`; CI fails below.
* **CI (`.github/workflows/ci.yml`):** install → ruff → mypy → pytest with coverage → build Docker image.
* **Type hints and docstrings** on every public function. No bare `except:`. No global mutable state; use dependency injection from `app.py`.
* **Pure functions** in `ict/` (DataFrame/array in → dataclass out) so they are deterministic and unit-testable.

### 3.3 Git Workflow
* `git init` first. Branch per phase: `feat/phase-03-data-streams`. Merge to `main` only when the phase DoD passes.
* **Conventional Commits:** `feat:`, `fix:`, `test:`, `docs:`, `refactor:`, `chore:`, `ci:`.
* Update `CHANGELOG.md` per phase. Tag releases (`v0.1.0` after Phase 9).
* `.gitignore` must exclude `.env`, `data/`, `out/`, `__pycache__/`, `.venv/`, `*.db`.

### 3.4 `AGENTS.md` (create this file in the repo root)
```markdown
# Rules for AI coding agents working in this repo
- Read SPECIFICATION_V2.md before any change. Follow the phase order.
- Never commit secrets. Never print TELEGRAM_BOT_TOKEN, API keys, or .env contents.
- All code in src/ict_scanner/. Business logic never imports FastAPI, Telegram, or SQLAlchemy directly
  (use the interfaces in domain/, repositories, and notifications/).
- ict/ functions must be pure and deterministic. Never use the still-forming candle (closed candles only).
- Every new feature needs tests. Run `make lint type test` before finishing a task; all must pass.
- Use structured logging (structlog), never print().
- Use UTC timezone-aware datetimes everywhere.
- Follow Conventional Commits. Update CHANGELOG.md and docs/ when behavior changes.
- Ask before adding a new dependency; justify it in the PR/commit message.
```

### 3.5 `Makefile` targets (must exist)
`install`, `lint`, `format`, `type`, `test`, `cov`, `run`, `sample-chart`, `test-alert`, `docker-build`, `docker-up`, `docker-logs`, `migrate`, `clean`.

### 3.6 Documentation Deliverables
`README.md` (with a sample alert screenshot generated by `make sample-chart`), `docs/architecture.md` (include the Section 2 diagram), `docs/strategy.md`, `docs/charting.md`, `docs/deployment.md`, `docs/runbook.md`.

---

## 4. Watchlist (10–15 Pairs, editable in `pairs.yaml` and from the dashboard)

```yaml
pairs:
  - {symbol: "EUR/USD", asset_class: forex,  provider: twelvedata, active: true}
  - {symbol: "GBP/USD", asset_class: forex,  provider: twelvedata, active: true}
  - {symbol: "USD/JPY", asset_class: forex,  provider: twelvedata, active: true}
  - {symbol: "AUD/USD", asset_class: forex,  provider: twelvedata, active: true}
  - {symbol: "GBP/JPY", asset_class: forex,  provider: twelvedata, active: true}
  - {symbol: "XAU/USD", asset_class: forex,  provider: twelvedata, active: true}   # Gold
  - {symbol: "NAS100",  asset_class: index,  provider: twelvedata, active: true}
  - {symbol: "US30",    asset_class: index,  provider: twelvedata, active: true}
  - {symbol: "BTC/USDT",asset_class: crypto, provider: ccxt, active: true}
  - {symbol: "ETH/USDT",asset_class: crypto, provider: ccxt, active: true}
  - {symbol: "SOL/USDT",asset_class: crypto, provider: ccxt, active: true}
```
Each entry also holds provider-specific symbol mappings (e.g., TwelveData `NDX`, `DJI`) and pip/tick size for position-size math.

---

## 5. Live 24/7 Data Layer (Requirement R1)

### 5.1 Streaming Design
* **Crypto:** `ccxt.pro` `watch_ohlcv` / `watch_trades` WebSockets (Binance public streams, no API key needed).
* **Forex / Gold / Indices:** TwelveData **WebSocket** price stream (or OANDA v20 streaming pricing as alternative). Ticks go through `candle_builder.py` to build 1M/5M/15M/1H/4H/1D candles.
  * **Honest note:** real-time forex/index streaming requires a paid TwelveData plan (or a free OANDA practice account for streaming). If only a free REST tier is available, the provider falls back to **REST polling every 10–15 seconds** for the latest candle. Make this a config switch: `FOREX_FEED_MODE=stream|poll`.
* **Candle store:** in-memory ring buffers (e.g., 1,500 candles per symbol/timeframe), warmed up at startup via REST history backfill, then updated live.
* **Closed-candle events:** the builder emits `CandleClosed(symbol, timeframe, candle)`; the pipeline subscribes to 5M and 15M closes.

### 5.2 Reliability (it must truly run forever)
* **Auto-reconnect** with exponential backoff + jitter on every stream.
* **Gap detection & backfill:** after a reconnect, compare the last stored candle time with now and fetch missing candles via REST before analysis resumes.
* **Staleness watchdog:** if no tick for a symbol within `STALE_AFTER_SECONDS` (default 90 while market open) → mark `DEGRADED`, attempt reconnect, and send a one-time Telegram **ops alert** (`⚠️ Feed stale: EUR/USD`). Send a recovery message when healthy again.
* **Market calendar:** forex/index closed from Friday ~21:00 UTC to Sunday ~21:00 UTC. During closure the scanner idles (no false stale alarms), crypto continues.
* **Supervisor:** every long-running task (streams, pipeline, outcome tracker) is wrapped in a supervisor that restarts it on crash and logs the exception.
* **Daily heartbeat:** one Telegram message at 00:00 UTC: uptime, pairs active, setups found/alerted in the last 24h.
* **Process level:** Docker `restart: always` + healthcheck. Container survives VPS reboots (Docker enabled at boot).

---

## 6. ICT Analysis Engine (Deterministic)

### 6.1 Multi-Timeframe Pipeline
| Layer | Timeframes | Purpose |
|-------|-----------|---------|
| HTF | 1D, 4H | Bias, major BSL/SSL, PDH/PDL, premium/discount of the larger range |
| ITF | 1H, 15M | Structure confirmation, unmitigated FVG/OB, dealing range |
| LTF | 5M (optionally 1M) | Entry trigger, precise SL, TP |

### 6.2 Detection Rules (all use **closed candles only**)
1. **Swing High/Low (5-bar fractal)** — confirmed 2 candles after forming (no repainting).
2. **Liquidity pools:** swing highs/lows, equal highs/lows (within `EQ_TOLERANCE` of ATR), previous day/week high-low, Asian range high/low.
3. **Sweep:** wick beyond a pool, close back inside (BSL → bearish bias, SSL → bullish bias).
4. **MSS + Displacement:** within `MSS_LOOKBACK_CANDLES` (default 10) after the sweep, a candle **body close** beyond the last opposing swing, with body ≥ `DISPLACEMENT_ATR_MULTIPLIER` (default 1.5) × ATR(14).
5. **FVG** (3-candle imbalance) created by the displacement leg; tracked until mitigated.
6. **Order Block:** last opposite-colored candle before the displacement leg.
7. **Dealing range & Premium/Discount:** from the swept extreme to the MSS-confirming extreme. Equilibrium = 50%. BUY entries must be in Discount, SELL entries in Premium.
8. **Fibonacci (drawn and used):** retracement of the dealing range with levels `0, 0.236, 0.382, 0.5, 0.618, 0.705, 0.786, 1`. **OTE zone = 0.618–0.786**. Extensions `-0.27, -0.62, -1.0` for TP projections. Entry should sit inside the OTE zone and/or overlap an FVG/OB (confluence).
9. **Killzones (UTC):** London `07:00–10:00`, New York AM `12:00–15:00` (optionally London Close `15:00–17:00` as a flag, default off). Asian `00:00–06:00` is reference only.
10. **HTF bias filter:** setup direction must agree with HTF bias unless `ALLOW_COUNTER_TREND=true`.

### 6.3 Trade Plan Construction (`levels.py`)
* **Entry:** limit entry at the FVG midpoint (consequent encroachment) or OB open; whichever sits inside the OTE zone. If both, prefer the overlap.
* **Stop Loss:** beyond the sweep extreme + `SL_ATR_BUFFER` (default 0.25 × ATR).
* **TP1:** nearest opposing internal liquidity / 1:2 R (whichever is closer, min 1:2).
* **TP2:** next HTF liquidity pool or fib extension `-0.27`.
* **Reject** if `rr_to_tp1 < MIN_RR` (default 2.0), if entry is outside Discount/Premium alignment, or if the FVG is already mitigated.
* **Setup lifecycle states:** `PENDING` (price hasn't reached entry) → `TRIGGERED` (entry touched) → `TP1_HIT` / `TP2_HIT` / `STOPPED` / `EXPIRED` (not filled within `SETUP_EXPIRY_HOURS`, default 12) / `INVALIDATED` (price closes beyond invalidation before entry).

### 6.4 Rule-Based Confluence Score (0–100, `scoring.py`)
Weighted, transparent, configurable:
| Factor | Points |
|--------|-------|
| HTF bias aligned | 20 |
| Liquidity sweep of a significant pool (HTF/PDH/PDL/equal highs-lows) | 15 |
| MSS with displacement ≥ threshold | 15 |
| Entry in correct Premium/Discount | 10 |
| Entry inside OTE (0.618–0.786) | 10 |
| FVG + OB overlap at entry | 10 |
| Inside killzone | 10 |
| R:R ≥ 3 to TP2 | 5 |
| Clear target liquidity exists | 5 |

---

## 7. Chart Renderer — "Mark Every Tool on the Chart" (Requirement R2)

### 7.1 Output
* Format: **PNG, 1600×900**, dark TradingView-style theme, produced in a worker thread (`asyncio.to_thread`) with matplotlib's `Agg` backend (headless).
* Per alert, render **2 images** sent as a Telegram album:
  1. **Entry chart** (LTF/ITF 15M or 5M, ~120–150 candles) — full annotation, shows the trade.
  2. **HTF context chart** (4H, ~100 candles) — bias, major liquidity, premium/discount.
* Header on every chart: `SYMBOL • TF • Direction • Confluence XX% • timestamp UTC`. Footer watermark: bot name + "Not financial advice".

### 7.2 Everything the Chart Must Draw
| Object | Drawing | Color (default theme) |
|--------|---------|------|
| Candles | Standard OHLC candles | Green / Red |
| Swing highs/lows | Small triangle markers + "SH/SL" | Gray |
| **BSL / SSL liquidity lines** | Horizontal dashed line from the pool's origin to the sweep, label "BSL" / "SSL" (+ "swept ✓") | Orange |
| **Sweep marker** | Arrow at the sweeping wick + label "Liquidity Sweep" | Yellow |
| Equal highs/lows | Dotted line with "EQH"/"EQL" | Orange |
| PDH / PDL | Thin horizontal lines with labels | Light blue |
| **Asian Range box** | Shaded rectangle 00:00–06:00 UTC high-to-low | Gray 15% alpha |
| **Killzone shading** | Vertical translucent band for London / New York AM | Blue/Purple 8% alpha |
| **MSS line** | Solid line across the broken swing + label "MSS" / "BOS" | White |
| **Displacement candle** | Highlighted outline + "Displacement 1.8×ATR" | Cyan |
| **FVG box** | Rectangle from creation candle extending right to current price (or until mitigated), label "FVG" | Teal 25% alpha |
| **Order Block box** | Rectangle on the OB candle extending right, label "OB" | Blue 25% alpha |
| **Premium / Discount zones** | Shaded halves of the dealing range with **EQ (50%) dashed line**, labels "PREMIUM" / "DISCOUNT" | Red-ish / Green-ish 8% alpha |
| **Fibonacci retracement** | Anchor-to-anchor diagonal + horizontal levels (0, 0.236, 0.382, 0.5, 0.618, 0.705, 0.786, 1) with % labels; **OTE zone (0.618–0.786) highlighted** | Gold lines, gold 15% alpha OTE |
| **Fib extensions / targets** | -0.27, -0.62 dotted lines | Gold dotted |
| **Entry line** | Solid horizontal line, label `ENTRY 1.08450` + arrow marker | Blue |
| **Stop Loss** | Red horizontal line + label `SL 1.08320` | Red |
| **TP1 / TP2** | Green horizontal lines + labels `TP1 1.08710`, `TP2 1.08950` | Green |
| **Long / Short position tool** | TradingView-style box: **green reward box** (entry→TP) and **red risk box** (entry→SL) extending ~25 candles to the right, with a center label `LONG • R:R 1:3.2` or `SHORT • R:R 1:2.8` | Green / Red 20% alpha |
| Current price | Line + price tag on right axis | White |
| Legend | Small legend box listing drawn elements | — |

### 7.3 Implementation Contract
* `charting/layers.py` exposes one pure function per object (`draw_fvg(ax, fvg)`, `draw_fib(ax, fib)`, `draw_position_tool(ax, plan)`…). `renderer.py` composes them in a fixed z-order (zones → lines → candles → labels → position tool → header).
* Renderer input: `RenderRequest(setup, candles_ltf, candles_htf, theme)` → output: `list[bytes]` (PNG).
* Auto-scale the y-axis to include SL, TPs, and fib extensions with 5% padding. Avoid label overlap (simple vertical nudging).
* **Golden-image tests:** render fixtures and compare to `tests/golden/*.png` with a tolerance (e.g., `pixelmatch`/`PIL ImageChops`) to catch drawing regressions.
* `make sample-chart` renders a showcase image with **all** objects for `README.md`.

---

## 8. AI Analyst Layer

### 8.1 Role
The deterministic engine finds setups; the LLM **reviews and explains** them. It never invents levels — it receives the engine's levels and must justify or reject.

### 8.2 Prompt (system + user)
```text
[SYSTEM]
You are a Lead Quantitative ICT Analyst. Strictly evaluate algorithmic trading setups against
institutional order-flow principles. Be objective; reject weak or contradictory setups.
Use ONLY the data provided; do not invent price levels. Output valid JSON only, no markdown.

[USER]
Evaluate this setup:
- Asset: {symbol} | Killzone: {session_name}
- HTF (4H) bias: {htf_bias} | ITF (15M) trend: {itf_trend}
- Direction: {direction}
- Liquidity swept: {sweep_description} at {sweep_level}
- MSS: {mss_description}, displacement = {displacement_atr}x ATR
- FVG: [{fvg_low} - {fvg_high}] | Order Block: [{ob_low} - {ob_high}] | OTE zone: [{ote_low} - {ote_high}]
- Dealing range: {range_low} - {range_high}; entry at {entry_pct}% of range ({zone_name})
- Levels: Entry={entry_price}, SL={stop_loss}, TP1={tp1}, TP2={tp2} (R:R TP1=1:{rr1}, TP2=1:{rr2})
- Rule-based confluence score: {rule_score}/100
- Key levels nearby: {key_levels}

Respond in this JSON format:
{
  "probability_score": <int 1-100>,
  "market_bias": "<Bullish | Bearish | Neutral>",
  "headline": "<one-line summary of the setup>",
  "thesis": "<3-5 sentences: why this entry makes sense step by step (sweep → MSS → FVG/OB → OTE → target)>",
  "why_take_it": ["<reason 1>", "<reason 2>", "<reason 3>"],
  "risks": ["<risk 1>", "<risk 2>"],
  "invalidation": "<exact price action that cancels this setup>",
  "confluence_checklist": [{"factor": "<name>", "present": <bool>}],
  "management_plan": "<e.g., move SL to breakeven at TP1, partials, trailing>"
}
```

### 8.3 Behavior
* Validate with Pydantic; retry once on malformed JSON; on failure **do not alert** (log + health record).
* Compute `approved` **in code**.
* **Final probability** = `0.6 × LLM score + 0.4 × rule score` (weights configurable). Show it labeled **"Confluence Probability"**.
* **Historical calibration:** once ≥ 30 closed setups exist for the same `(asset_class, session, direction)` bucket, the alert also shows **"Historical win rate (this setup type): XX% over N trades"** from `tracking/stats.py`. Until then, show "Historical stats: collecting data (N/30)".
* Alert only if `final_probability ≥ MIN_PROBABILITY_THRESHOLD` (default 75) **and** rules passed.
* One LLM call per unique `dedupe_key`; cooldown per symbol (default 60 min).
* Timeout 30s, temperature 0.2. Provider switch via `AI_PROVIDER`.

---

## 9. Telegram Trade Desk (Requirements R3 & R4)

Telegram bot is already created; use the Bot API via `python-telegram-bot` (async) or direct `httpx` calls.

### 9.1 Delivery Sequence per Alert
1. `sendMediaGroup` — album of **2 annotated charts** (entry chart first, HTF chart second). Caption on the first image (≤ 1,024 chars): headline + direction + probability + entry/SL/TP1/TP2.
2. `sendMessage` — the **full trade-desk message** (≤ 4,096 chars; split if longer) with inline buttons:
   * `✅ Taken` | `⏭ Skipped` | `📊 Stats` (callback handlers store the owner's decision in DB for later analysis).
3. Follow-up **status updates** as replies to the original message: `🎯 TP1 hit (+2.0R)`, `✅ TP2 hit (+3.4R)`, `🛑 Stopped (-1R)`, `⌛ Expired (not filled)`, `❌ Invalidated before entry`.

### 9.2 Full Trade-Desk Message Template
```text
🚨 ICT SETUP — {symbol} — {direction_emoji} {direction}
━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 {headline}
🕒 {timestamp_utc} UTC | 🔔 Killzone: {session_name} | ⏱ Entry TF: {entry_tf}

📊 CONFLUENCE PROBABILITY: {probability}%
   ├ AI score: {ai_score}% | Rule score: {rule_score}/100
   └ Historical win rate (this setup type): {hist_stats}

🎯 TRADE PLAN
• Order type: LIMIT {direction} @ {entry_price}
• Stop Loss: {stop_loss}  ({sl_distance} {unit})
• TP1: {tp1}  (R:R 1:{rr1}) → take {tp1_partial}% off
• TP2: {tp2}  (R:R 1:{rr2})
• Entry zone: FVG [{fvg_low} – {fvg_high}] / OTE [{ote_low} – {ote_high}]
• Valid until: {expiry_utc} UTC (cancel if not filled)

🧠 WHY TAKE THIS ENTRY
{thesis}

✅ REASONS / CONFLUENCES
{why_take_it_bullets}

✔️ CHECKLIST
{confluence_checklist}   # e.g. ✅ HTF bias aligned  ✅ Liquidity swept  ✅ MSS+displacement  ✅ OTE  ✅ Killzone

🧭 MULTI-TIMEFRAME CONTEXT
• 1D/4H bias: {htf_bias} | 15M trend: {itf_trend}
• Swept: {sweep_description}
• Next liquidity target: {target_description}
• Nearby key levels: {key_levels}

⚠️ RISKS
{risks_bullets}

⛔ INVALIDATION
{invalidation}

🛠 MANAGEMENT PLAN
{management_plan}

💰 POSITION-SIZE EXAMPLE (risk {risk_pct}% of ${account_balance} = ${risk_amount})
{position_size_example}
   e.g. Forex: ≈ {lots} lots | Crypto: ≈ {units} units | Index/Gold: ≈ {contracts} contracts
   (Estimate only — verify pip/tick value with your broker.)

⚠️ Informational only. Not financial advice. Trade at your own risk.
━━━━━━━━━━━━━━━━━━━━━━━━━━
```
* "Example" section = the **position-size worked example** above plus the annotated chart (which acts as a visual example of the trade). Account size and risk % come from `.env` (`ACCOUNT_BALANCE`, `RISK_PERCENT`) and are editable in the dashboard.
* Use HTML parse mode (escape all dynamic text with `html.escape`) to avoid Markdown formatting errors.
* Telegram rate limits: max ~30 msgs/sec globally, 1 msg/sec per chat → use an outbound queue with retry/backoff (`RetryAfter` handling).

### 9.3 Other Telegram Messages
* **Startup:** `✅ ICT Scanner online — {n} pairs live`.
* **Ops alerts:** feed stale / recovered, AI provider errors, DB errors (rate-limited to avoid spam).
* **Daily heartbeat** and **weekly performance summary** (Sunday 21:00 UTC): setups, alerts, win rate, avg R, best/worst pair.
* **Commands:** `/status`, `/pairs`, `/pause`, `/resume`, `/last`, `/stats`, `/chart SYMBOL` (renders the current annotated chart on demand), `/risk 1`, `/help`. Restrict **all** commands to `TELEGRAM_CHAT_ID` (ignore other users).

### 9.4 Email (optional secondary channel)
Same content as HTML email with the chart PNGs attached inline (CID). Disabled by default (`EMAIL_ENABLED=false`).

---

## 10. Database (SQLAlchemy 2.0 async + Alembic)

Use **Alembic migrations**; no manual DDL. SQLite (WAL, `busy_timeout=5000`) by default, PostgreSQL-ready.

Tables (ORM models; reference columns):
* `pairs_config(id, symbol UNIQUE, asset_class, provider, is_active, timeframes, pip_size, updated_at)`
* `setups(id, symbol, direction, session_name, entry_tf, status, sweep_level, sweep_type, mss_level, displacement_atr, fvg_low, fvg_high, ob_low, ob_high, ote_low, ote_high, range_low, range_high, entry_price, stop_loss, tp1, tp2, rr1, rr2, rule_score, dedupe_key UNIQUE, created_at, expires_at, triggered_at, closed_at, outcome_r)`
* `ai_evaluations(id, setup_id FK, ai_score, final_probability, market_bias, headline, thesis, why_take_it JSON, risks JSON, invalidation, management_plan, checklist JSON, approved, provider, model, created_at)`
* `chart_artifacts(id, setup_id FK, kind 'ENTRY'|'HTF', file_path, created_at)`
* `alert_logs(id, setup_id FK, channel, message_id, status, response_payload, dispatched_at)`
* `trade_decisions(id, setup_id FK, decision 'TAKEN'|'SKIPPED', decided_at)`  — from Telegram buttons
* `setup_events(id, setup_id FK, event 'TRIGGERED'|'TP1_HIT'|'TP2_HIT'|'STOPPED'|'EXPIRED'|'INVALIDATED', price, occurred_at)`
* `system_health_logs(id, component, status, message, recorded_at)`
* `app_settings(key PK, value, updated_at)` — runtime-editable settings from the dashboard.

Access only through `db/repositories.py`. Data retention: prune chart files older than `CHART_RETENTION_DAYS` (default 30).

---

## 11. Admin API & Dashboard

* **Auth:** header `X-API-Key: <ADMIN_API_KEY>` on everything except `GET /api/health`. Rate-limit login attempts. Put behind HTTPS (Caddy/Nginx) in production.
* **Routes:**
  * `GET /api/health` — component status, feed latency per symbol, last candle time, uptime
  * `GET /api/pairs`, `POST /api/pairs/toggle`
  * `GET /api/setups` (filters: symbol, status, date), `GET /api/setups/{id}` (full detail + chart URLs)
  * `GET /api/charts/{setup_id}/{kind}` — serves the PNG
  * `GET /api/stats` — win rate, avg R, per symbol/session
  * `GET/POST /api/settings` — threshold, MIN_RR, risk %, killzones, scan params
  * `GET /api/logs`
  * `POST /api/scan/manual` — force an analysis run
  * `POST /api/test-alert` — sends a sample alert + chart to Telegram
* **Dashboard (`GET /`):** responsive, dark. Panels: live feed status per pair (green/yellow/red), active setups with embedded chart thumbnails, history table, stats cards, settings form, log viewer.

---

## 12. Deployment (24/7 VPS)

### 12.1 `Dockerfile` (multi-stage, non-root)
```dockerfile
FROM python:3.11-slim AS builder
WORKDIR /build
ENV PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml ./
COPY src ./src
RUN pip install --prefix=/install .

FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 TZ=UTC MPLBACKEND=Agg
RUN apt-get update && apt-get install -y --no-install-recommends curl fonts-dejavu-core && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 10001 appuser
WORKDIR /app
COPY --from=builder /install /usr/local
COPY alembic.ini ./
COPY migrations ./migrations
COPY src ./src
RUN mkdir -p /app/data && chown -R appuser:appuser /app
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --retries=3 CMD curl -f http://localhost:8000/api/health || exit 1
CMD ["sh", "-c", "alembic upgrade head && uvicorn ict_scanner.api.main:app --host 0.0.0.0 --port 8000"]
```
*The scanner/orchestrator starts inside the FastAPI `lifespan` handler (single process).*

### 12.2 `docker-compose.yml`
```yaml
services:
  ict-scanner:
    build: .
    container_name: ict_scanner
    restart: always
    ports:
      - "127.0.0.1:8000:8000"     # expose via reverse proxy with HTTPS, not directly
    env_file: .env
    volumes:
      - ./data:/app/data
    logging:
      driver: json-file
      options: {max-size: "20m", max-file: "5"}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```
*Optional second service: `caddy` for automatic HTTPS in front of the app.*

### 12.3 `.env.example`
```env
# Runtime
ENVIRONMENT=production
LOG_LEVEL=INFO
DATABASE_URL=sqlite+aiosqlite:///data/trading_bot.db
ADMIN_API_KEY=change_me_to_a_long_random_string

# Live data
FOREX_FEED_MODE=stream            # stream | poll
CRYPTO_EXCHANGE=binance
TWELVE_DATA_API_KEY=
OANDA_API_KEY=
OANDA_ACCOUNT_ID=
STALE_AFTER_SECONDS=90

# AI
AI_PROVIDER=openai                # openai | anthropic | openrouter
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
AI_MODEL=gpt-4o
MIN_PROBABILITY_THRESHOLD=75
AI_WEIGHT=0.6

# Strategy
MIN_RR=2.0
MSS_LOOKBACK_CANDLES=10
DISPLACEMENT_ATR_MULTIPLIER=1.5
SL_ATR_BUFFER=0.25
ALLOW_COUNTER_TREND=false
SETUP_EXPIRY_HOURS=12
SYMBOL_COOLDOWN_MINUTES=60

# Risk / position-size example
ACCOUNT_BALANCE=1000
RISK_PERCENT=1

# Telegram (bot already created)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
SEND_CHART_ALBUM=true
SEND_HEARTBEAT=true

# Email (optional)
EMAIL_ENABLED=false
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASS=
ALERT_RECIPIENT_EMAIL=

# Charts
CHART_RETENTION_DAYS=30
```

### 12.4 VPS Setup
```bash
sudo apt update && sudo apt install -y git docker.io docker-compose-v2
sudo systemctl enable --now docker
git clone <your-repo> /opt/ict-scanner && cd /opt/ict-scanner
cp .env.example .env && nano .env          # fill TELEGRAM_*, API keys, ADMIN_API_KEY
sudo docker compose up -d --build
sudo docker compose logs -f
# Verify bot + chart rendering:
sudo docker compose exec ict-scanner python scripts/send_test_alert.py
```
Recommended VPS: 2 vCPU / 2–4 GB RAM / Ubuntu 22.04+ (chart rendering and indicators are CPU-light; memory mostly holds candle buffers).

---

## 13. Testing Strategy

* **Unit tests:** every `ict/` module with fixtures containing known patterns (bullish & bearish sweep→MSS→FVG; wick-only no MSS; sweep with no displacement; outside killzone; mitigated FVG).
* **Look-ahead test:** running the engine on candles `[0..n]` vs `[0..n+k]` must produce identical results for candle `n` (proves no repainting).
* **Charting tests:** every layer renders without error; golden-image comparison; extreme cases (very tight range, missing OB).
* **Notification tests:** formatter output length limits, HTML escaping, album + message sequence with a fake Telegram client.
* **Integration test:** fake data provider streams a prepared candle sequence → pipeline → fake AI → chart rendered → fake Telegram receives **album + full message**; assert content includes entry, SL, TP, probability, thesis, invalidation.
* **Resilience test:** fake provider drops connection → reconnect + gap backfill → no duplicate/missing candles.
* **Outcome tracker test:** feed prices that hit TP1, TP2, SL, expiry → correct status transitions and R values.

---

## 14. Phased Implementation Plan for Antigravity

Each phase = its own branch, passes `make lint type test`, updates docs/CHANGELOG, merged with a Conventional Commit.

- [ ] **Phase 0 — Repo Foundation:** `git init`, full repo layout (Section 3.1), `pyproject.toml`, Makefile, ruff/mypy/pytest config, pre-commit, CI workflow, `.gitignore`, `.editorconfig`, `AGENTS.md`, `README.md` skeleton, `CONTRIBUTING.md`, `CHANGELOG.md`. **DoD:** `make install lint type test` passes on an empty-but-wired project; CI file valid.
- [ ] **Phase 1 — Config & Domain:** `settings.py`, `pairs.yaml`, `domain/enums.py`, `domain/models.py` (frozen dataclasses/Pydantic). **DoD:** settings load from `.env.example`; domain unit tests pass.
- [ ] **Phase 2 — Database:** async SQLAlchemy, ORM models (Section 10), Alembic initial migration, repositories, WAL pragmas. **DoD:** `alembic upgrade head` creates all tables; repository tests pass.
- [ ] **Phase 3 — Live Data Layer:** providers (ccxt.pro, TwelveData WS/REST, OANDA optional), `candle_builder`, `candle_store`, backfill, reconnect, watchdog, market calendar. **DoD:** against live crypto stream, 5M candles close and appear in the store; fake-provider resilience tests pass.
- [ ] **Phase 4 — ICT Engine:** fractals, liquidity, structure, imbalance, order blocks, premium/discount, fibonacci, killzones, levels, scoring, engine state machine. **DoD:** unit + look-ahead tests pass, ≥85% coverage on `ict/`.
- [ ] **Phase 5 — Chart Renderer:** theme, primitives, layers (every object in Section 7.2), renderer, `scripts/render_sample_chart.py`, golden images. **DoD:** `make sample-chart` outputs a PNG showing **all** objects correctly; charting tests pass; owner can visually review it.
- [ ] **Phase 6 — AI Analyst:** prompts, schemas, provider adapters, scoring blend, retries, dedupe/cooldown, mocked tests. **DoD:** malformed-JSON and timeout paths handled; no alert on failure.
- [ ] **Phase 7 — Telegram Trade Desk:** formatter (Section 9.2), album + message sender, inline buttons + callbacks, status-reply updates, commands (restricted to owner), outbound queue/backoff, `scripts/send_test_alert.py`. **DoD:** running `make test-alert` delivers the album + full message to the owner's Telegram.
- [ ] **Phase 8 — Orchestration & Outcome Tracking:** pipeline (candle-close → engine → AI → chart → alert → persist), supervisor, outcome tracker, stats, heartbeat/weekly summary. **DoD:** integration test passes end-to-end with fakes; live dry-run on crypto produces setups/logs without crashing for 1 hour.
- [ ] **Phase 9 — API & Dashboard:** routes (Section 11), auth, dashboard UI with chart thumbnails and feed status. **DoD:** all routes tested; unauthorized requests rejected; dashboard shows live feed health.
- [ ] **Phase 10 — Docker & Production Hardening:** multi-stage Dockerfile, compose, logging rotation, healthcheck, docs (`deployment.md`, `runbook.md`, `architecture.md`, `strategy.md`, `charting.md`). **DoD:** `docker compose up --build` healthy; container auto-restarts after `docker kill`; 24-hour soak test shows no memory growth, no crashes. Tag `v0.1.0`.

---

## 15. Acceptance Checklist (Owner Sign-Off)

- [ ] System streams live data for all active pairs 24/7 and recovers automatically from disconnects.
- [ ] A detected setup produces a Telegram **album of annotated charts** showing: liquidity lines, sweep, MSS, FVG/OB boxes, premium/discount, Fibonacci + OTE, entry, SL, TP1/TP2, and the long/short position box.
- [ ] The Telegram message includes: probability, entry/SL/TP, why take it, reasons, checklist, MTF context, risks, invalidation, management plan, and position-size example.
- [ ] Follow-up status updates arrive when TP/SL/expiry occurs.
- [ ] Ops alerts arrive when a feed goes stale.
- [ ] Repo passes lint, type-check, tests, and CI; docs are complete; project is cleanly organized per Section 3.
- [ ] Runs unattended on the VPS for 7 days.

---

## 16. Important Limits & Honest Notes

* **Probability ≠ guarantee.** The score blends an AI opinion and rule-based confluence. Only the outcome tracker's historical win rate (after enough trades) reflects real performance. Forward-test in alert-only mode for several weeks before risking real money.
* **No auto-trading.** This system alerts and analyzes; the owner places trades manually.
* **Data quality matters.** True real-time forex/index data needs a streaming-capable provider plan; free tiers may be delayed or rate-limited (see Section 5.1).
* **Secrets:** if the Telegram bot token is ever pasted into a chat, repo, or screenshot, revoke it in @BotFather (`/revoke`) and generate a new one.
* Alerts are informational and **not financial advice**.
