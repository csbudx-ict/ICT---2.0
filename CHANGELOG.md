# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Multi-service production supervisor script (`start.sh`) running FastAPI backend (`ict_scanner`) and Next.js frontend (`ict-scanner-dashboard`) concurrently with graceful SIGTERM/SIGINT signal handling.
- Multi-stage `Dockerfile` and updated `docker-compose.yml` for 24/7 containerized Botkeep deployment with persistent volume configuration.
- Comprehensive `DEPLOYMENT.md` deployment guide detailing Botkeep dashboard setup, environment variables hookup (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, AI and provider keys), volume persistence, and verification.
- Next.js reverse proxy rewrites in `next.config.mjs` routing `/api` and `/charts` requests internally to the FastAPI backend.
- Phase 0: Repo foundation and professional standards (CI/CD, lint, typing, directory layout).
- A closed-candle market WebSocket API and live ICT dashboard at `/live-demo`.
- Closed-candle ICT module calculations for FVG, order blocks, OTE Fibonacci, breaker blocks, Premium/Discount, BOX/liquidity pools, and the Master Sniper confluence gate; live dashboard toggles and strategy notes.
- Dedicated Unicorn Setup, three-candle Silver Bullet FVG, and displacement-confirmed Institutional Order Block signals.
- A real-provider dashboard WebSocket at `/api/ws/dashboard`; the main dashboard now displays active-pair provider status and closed-candle module signals, with live module selection and refresh controls.
- SQLAlchemy's asyncio extra is declared so clean installs include the async engine's greenlet runtime dependency.
- SQLite database parent directories are created before engine initialization so local dashboard startup works with nested database paths.
- An “All Detected Entries” dashboard modal lists active directional setups across connected pairs, ranks top-two suggestions transparently, and dispatches all or up to two selected setups to Telegram.
- Advanced ICT analysis for confirmed inducement swings, Turtle Soup sweeps, mitigation and rejection blocks, normalized PD arrays, and UTC killzone context; live dashboard pair snapshots expose these readouts.
- A deterministic walk-forward Turtle Soup backtester with next-candle entries, stop-first same-candle resolution, bounded holding periods, and structured result logging.

### Changed
- OTE Fibonacci levels now use `[0, 1, 0.618, 0.705, 0.79, -1, -0.62, -0.27, 0.5]`, with the 0.705 level highlighted as the sweet spot.
- The scheduled scanner now converts provider OHLC frames into UTC-aware domain candles before running ICT analysis.
- Replaced the synthetic `/live-demo` WebSocket stream with Twelve Data polling for closed 1-minute EUR/USD, GBP/USD, and XAU/USD candles at a configurable one-minute cadence; the dashboard now exposes the requested seven ICT modules. Module changes immediately recalculate cached closed candles without extra API calls.
- Removed the dashboard theme toggle and its light-theme switching rules. Telegram sends now report missing credentials as failures instead of mock successes.
- Restored the control room's fixed light palette and light-only browser color scheme without reintroducing a theme toggle.
- Made the dashboard accept older WebSocket snapshots without the optional detected-entry list, preserving live pair and signal cards while the entry modal falls back to an empty list.
- Initialized and shut down the Telegram Bot client for modal dispatches, batch-sent entries in one client session, and surfaced delivery results inside the open modal, including connection and timeout errors.
- Hardened the dashboard WebSocket against stale close events and half-open connections; automatic reconnect now restores the active socket reference and heartbeat status.
