# Antigravity Workspace Rules: ICT Trading Bot

## Core Directives
1. Strictly follow `SPECIFICATION.md`. Do not invent new libraries or alter the core architecture without permission.
2. Build modularly: Keep technical math (`core/ict/`), LLM logic (`core/ai/`), and delivery (`notifications/`) in separate folders.
3. Every Python module must have strong type hints and clean error handling (try/except with logging).
4. Do not run destructive terminal commands (`rm -rf`, modifying system configs).
5. Before completing any phase, write a unit or integration test in `tests/` and verify that it passes.
