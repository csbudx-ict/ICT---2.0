# 24/7 ICT Scanner & AI Analyst

An automated, headless algorithmic trading scanner operating 24/7 on a cloud VPS across selected Forex, Crypto, and Index pairs. 

This system uses pure ICT algorithmic concepts (Liquidity Sweeps, Market Structure Shifts, Fair Value Gaps, Order Blocks, and Session Killzones). All detected setups are evaluated by an AI Agent (OpenAI/Anthropic) to verify confluence and assign a probability score before firing alerts to Telegram and Email.

**Disclaimer:** This is an alerting tool. It does NOT place trades automatically and is not financial advice.

## Features
- **Deterministic ICT Engine:** Strict multi-timeframe algorithm enforcing MSS + Displacement.
- **AI Evaluator Layer:** Confluence scoring to filter out weak signals.
- **Web Admin Panel:** Manage Active Pairs, Adjust Thresholds, View Logs.
- **Alert Dispatcher:** Beautiful Telegram & Email formats.
- **Dockerized for VPS:** Ready to run indefinitely.

## Deployment Instructions (Ubuntu VPS)

1. **Install Dependencies:**
   ```bash
   sudo apt update && sudo apt install -y git docker.io docker-compose-v2
   ```

2. **Clone Repository & Enter Directory:**
   ```bash
   git clone <your-repo-url> ict-trading-bot
   cd ict-trading-bot
   ```

3. **Configure Environment Variables:**
   ```bash
   cp .env.example .env
   nano .env
   ```
   *Make sure to configure your `ADMIN_API_KEY`! You'll need this to login to the Dashboard.*

4. **Start the Bot (Background):**
   ```bash
   sudo docker compose up -d --build
   ```

5. **Access the Dashboard:**
   Open your browser to `http://<your-vps-ip>:8000` and login with your `ADMIN_API_KEY`.

6. **View Logs:**
   ```bash
   sudo docker compose logs -f
   ```

## Development
Run the live-provider dashboard API locally without Docker:
```bash
python -m uvicorn ict_scanner.api.demo:app --reload --host 127.0.0.1 --port 8000
```
Run tests:
```bash
python -m pytest tests/
```

Open `http://localhost:3000` for the provider-backed control room. It loads active pair
configurations, reports missing providers or credentials as unavailable, and recalculates when a
module is toggled or **Scan now** is pressed. The `NEXT_PUBLIC_API_WS_URL` variable can override
the dashboard WebSocket URL if the API is hosted elsewhere.
Use **All Detected Entries** to review the latest directional signals across active pairs, select the
backend-prioritized top two or choose up to two manually, and send either the selected signals or all
current signals to Telegram. Configure `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in the backend
`.env`; Telegram dispatch reports missing credentials or delivery failures in the dashboard.

In a second terminal, start the Next.js dashboard:

```bash
cd ict-scanner-dashboard
npm run dev
```

Open `http://localhost:3000/live-demo` for the Twelve Data market scanner. The backend polls closed
one-minute candles for EUR/USD, GBP/USD, and XAU/USD using `TWELVE_DATA_API_KEY` from `.env`, then
streams provider status, candle data, and the seven selected ICT calculations to the dashboard
over the application's WebSocket. Polling is once per minute by default (set
`TWELVE_DATA_POLL_INTERVAL_SECONDS` to change it). Provider errors and missing credentials are
shown as unavailable; synthetic data is never used as a fallback. Twelve Data plan entitlements
and API quotas determine data freshness and availability.
