# 🚀 24/7 Production Deployment Guide: Botkeep

This guide walks you through deploying the **ICT Scanner V2** (FastAPI backend + Next.js Control Room dashboard) for 24/7 continuous operation on [Botkeep](https://botkeep.cloud).

---

## 🏗 Architecture Overview

The application runs two services concurrently inside a single container/environment:
1. **FastAPI Backend (`ict_scanner`)**:
   - Listens on port `8000`.
   - Runs database migrations via Alembic.
   - Hosts the background market scanner (`Scheduler`) inside FastAPI lifespan.
   - Scans live candle streams (Crypto via CCXT, Forex via Twelve Data), detects ICT setups (FVG, Order Blocks, MSS, Silver Bullet, Unicorn), runs AI reasoning evaluations, renders annotated charts, and dispatches Telegram alerts.
   - Exposes REST API and WebSockets (`/api/ws/dashboard`, `/api/ws/live-market`).
2. **Next.js Frontend (`ict-scanner-dashboard`)**:
   - Listens on port `3000`.
   - Provides the interactive live trading control room and EUR/USD demo terminal.
   - Pre-configured with automatic internal API and chart proxy rewrites pointing to the FastAPI backend.

Both processes are coordinated by the production supervisor script [`start.sh`](file:///start.sh), which provides automatic process health monitoring and graceful `SIGTERM`/`SIGINT` handling.

---

## 📋 Prerequisites Checklist

Before creating your Botkeep service, have the following ready:
- A [Botkeep](https://botkeep.cloud) account.
- Your Telegram Bot Token (`TELEGRAM_BOT_TOKEN`) and Telegram Chat ID (`TELEGRAM_CHAT_ID`).
- At least one AI API key (`GEMINI_API_KEY`, `OPENAI_API_KEY`, or `ANTHROPIC_API_KEY`).
- Market data API key (`TWELVE_DATA_API_KEY` for Forex/Indices).

---

## 🛠 Step 1: Deploying on Botkeep

### Option A: Dockerfile Deployment (Recommended)
1. In your **Botkeep Dashboard**, click **New Service** or **Create Project**.
2. Connect your Git repository or upload the project ZIP.
3. Set the **Deployment Method** to **Dockerfile**.
4. Botkeep will automatically detect the root [`Dockerfile`](file:///Dockerfile), run the multi-stage build (compiling Next.js and packaging Python 3.11 with Node.js), and start [`start.sh`](file:///start.sh).

### Option B: Custom Startup Command / Node.js Template
If you are deploying using Botkeep's Node.js or Python runtime template:
1. In the **Start Command** input box:
   - **Delete** any default command (such as `node index.js` or `npm start`).
   - **Replace** it with:
     ```text
     ./start.sh
     ```
   *(or `bash ./start.sh` / `chmod +x ./start.sh && ./start.sh`)*
2. In the **Build Command** input box (if using pre-start build):
   ```bash
   pip install -e . && cd ict-scanner-dashboard && npm install --legacy-peer-deps && npm run build && cd ..
   ```

---

## 💾 Step 2: Configure Persistent Storage (Crucial)

To ensure your SQLite database (`data/trading_bot.db`) and generated setup charts (`data/charts/`) persist across restarts and redeployments:

1. In the Botkeep project dashboard, go to the **Storage** or **Volumes** tab.
2. Add a persistent volume mount:
   - **Container Mount Path:** `/app/data` (or `./data` for native runs)
   - **Size:** 1 GB – 5 GB (sufficient for thousands of trade setups, logs, and chart images)

---

## 🔑 Step 3: Setting Environment Variables on Botkeep Dashboard

Navigate to your service's **Settings** ➔ **Environment Variables** (or **Config Vars**) tab in the Botkeep dashboard. Add the following variables:

### 1. Telegram Notifications
| Variable Name | Description | Example / Instructions |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Bot API token | Open Telegram, search `@BotFather`, send `/newbot`, and copy the HTTP API token (e.g. `7123456789:AAH...`). |
| `TELEGRAM_CHAT_ID` | Recipient Chat or Channel ID | Search `@userinfobot` on Telegram and send `/start` to get your numeric ID (e.g. `123456789`). For channels/groups, use the channel ID with `-100` prefix (e.g. `-1001987654321`). |

> [!TIP]
> Ensure you send `/start` to your bot from your Telegram account before running the bot so it has permission to send you direct messages.

### 2. Market Data Providers
| Variable Name | Description | Example / Default |
|---|---|---|
| `TWELVE_DATA_API_KEY` | API Key for Forex (EUR/USD, GBP/USD) & Indices | Free key from [twelvedata.com](https://twelvedata.com) |
| `CRYPTO_EXCHANGE` | CCXT Crypto Exchange | `binance` (or `bybit`, `okx`) |
| `OANDA_API_KEY` | Oanda v20 API Key (optional) | Leave blank if using Twelve Data |

### 3. AI Reasoning Engine
| Variable Name | Description | Recommended Setting |
|---|---|---|
| `AI_PROVIDER` | AI backend engine (`gemini`, `openai`, `anthropic`) | `gemini` |
| `GEMINI_API_KEY` | Google Gemini API key | Obtain from [Google AI Studio](https://aistudio.google.com/) |
| `AI_MODEL` | Target AI Model | `gemini-1.5-pro` (or `gpt-4o`, `claude-3-5-sonnet-20241022`) |
| `MIN_PROBABILITY_THRESHOLD`| Minimum AI confidence % required to dispatch Telegram alert | `75` |
| `OPENAI_API_KEY` | OpenAI API key (if `AI_PROVIDER=openai`) | `sk-...` |
| `ANTHROPIC_API_KEY` | Anthropic API key (if `AI_PROVIDER=anthropic`) | `sk-ant-...` |

### 4. Core System & Security
| Variable Name | Description | Default / Value |
|---|---|---|
| `ENVIRONMENT` | Execution environment | `production` |
| `ADMIN_API_KEY` | Secret token protecting admin routes & manual scan triggers | Generate a random 32-character string |
| `DATABASE_URL` | SQLite async database location | `sqlite+aiosqlite:///data/trading_bot.db` |
| `HOST` | Bind host address | `0.0.0.0` |
| `BACKEND_PORT` | FastAPI listening port | `8000` |
| `FRONTEND_PORT` | Next.js dashboard listening port | `3000` |
| `PORT` | Public port exposed by Botkeep | `3000` (or `8000`) |

### 5. Strategy Parameters (Optional Tuning)
| Variable Name | Description | Default |
|---|---|---|
| `SCAN_INTERVAL_SECONDS` | Interval between market scan cycles (seconds) | `300` (5 minutes) |
| `MIN_RR` | Minimum Risk to Reward ratio filter | `2.0` |
| `MSS_LOOKBACK_CANDLES` | Market Structure Shift lookback depth | `10` |
| `DISPLACEMENT_ATR_MULTIPLIER` | ATR displacement sensitivity multiplier | `1.5` |

---

## 🔍 Step 4: Verification & Live Health Checks

Once you hit **Deploy** in the Botkeep Dashboard:

1. **Check Live Console Logs:**
   Open the **Logs / Console** tab on Botkeep. You should see:
   ```text
   [Config] Host: 0.0.0.0
   [Config] Backend Port: 8000
   [Config] Frontend Port: 3000
   [Database] Running database migrations...
   [Backend] Launching FastAPI ICT Scanner API and background orchestrator...
   [Frontend] Launching Next.js Control Room Dashboard...
   INFO:     Uvicorn running on http://0.0.0.0:8000
   INFO:     Scheduler: Completed scan cycle successfully.
   Ready in 1200ms (Next.js)
   ```
2. **Telegram Heartbeat:**
   If your `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are configured correctly, the bot will automatically send a startup heartbeat message:
   > 🟢 *ICT Scanner V2 is online and monitoring.*
3. **Health Check Endpoint:**
   Test the HTTP health endpoint via browser or curl:
   ```bash
   curl -f http://<your-botkeep-url>/api/health
   # Response: {"status":"healthy"}
   ```
4. **Access Next.js Control Room:**
   Navigate to your assigned Botkeep URL (port 3000) to view live order flow, recent ICT setup triggers, and the EUR/USD demo terminal.

---

## 🧯 Troubleshooting Common Issues

### 1. Telegram alerts not arriving
- **Error:** `Telegram Unauthorized` or `Forbidden: bot was blocked by the user`.
- **Fix:** Ensure you opened a chat with your bot on Telegram and pressed `/start`. Double-check `TELEGRAM_BOT_TOKEN` for any trailing spaces.

### 2. Twelve Data rate limit error
- **Error:** `API limit reached` (Code 429).
- **Fix:** The free Twelve Data tier allows 8 API credits per minute. Keep `TWELVE_DATA_POLL_INTERVAL_SECONDS=60` and limit active monitored pairs to 1-2 forex symbols.

### 3. Container restarts unexpectedly
- **Error:** Out-of-memory (OOM) or non-zero exit code.
- **Fix:** Next.js building on small containers can consume RAM. Pre-building inside the multi-stage [`Dockerfile`](file:///Dockerfile) (as configured) avoids building inside low-memory runtime containers.

### 4. Database resets after redeployment
- **Error:** Previous trade setups disappear after a new deployment.
- **Fix:** Ensure a persistent volume is mounted to `/app/data`.
