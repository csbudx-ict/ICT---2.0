# AGENTS.md
# Rules for AI coding agents working in this repo
- Read SPECIFICATION_V2.md before any change. Follow the phase order.
- Never commit secrets. Never print TELEGRAM_BOT_TOKEN, API keys, or .env contents.
- All code in src/ict_scanner/. Business logic never imports FastAPI, Telegram, or SQLAlchemy directly (use the interfaces in domain/, repositories, and notifications/).
- ict/ functions must be pure and deterministic. Never use the still-forming candle (closed candles only).
- Every new feature needs tests. Run `make lint type test` before finishing a task; all must pass.
- Use structured logging (structlog), never print().
- Use UTC timezone-aware datetimes everywhere.
- Follow Conventional Commits. Update CHANGELOG.md and docs/ when behavior changes.
- Ask before adding a new dependency; justify it in the PR/commit message.
