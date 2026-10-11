# Algorithmic Backtests

## Curriculum

### Multi-timeframe fractal validation

When extending the current single-timeframe backtest, build each timeframe from
closed source candles, timestamp-aligned without forward leakage. Confirm a
five-bar fractal only after its two right-side bars close on that timeframe;
only then may a later lower-timeframe decision consume it. Current backtest
implementation evaluates 5M-style input candles and does not yet combine
Daily/4H/1H/15M context.

1. **Data preparation:** validate candle columns, chronological order, timezone,
   missing intervals, duplicates, and market/provider coverage.
2. **Signal timing:** calculate a signal only from information available at
   that candle's close; model execution no earlier than the next candle.
3. **Trade model:** specify entry, invalidation/stop, target, fees/slippage,
   expiry, and how ambiguous candles are resolved before running results.
4. **Evaluation:** report sample size, win rate, expectancy in R, drawdown,
   exposure, and performance by market/session; avoid relying on a single
   headline metric.
5. **Robustness:** use out-of-sample periods, multiple symbols/regimes, and
   sensitivity checks. Historical results do not guarantee future performance.

## Current Turtle Soup backtest

The walk-forward implementation can be run on historical closed candles:

```powershell
python -m ict_scanner.ict.backtesting .\candles.csv --reward-to-risk 2 --max-holding-candles 24
```

### Signal and execution definitions

- CSV columns: `timestamp,open,high,low,close`; `volume` is optional.
- Parseable naive timestamps are interpreted as UTC; timezone-aware timestamps
  are converted to UTC.
- A Turtle Soup signal uses pools formed before the trigger candle and requires
  a wick-through followed by a close back across the pool.
- Entry is the open of the next candle. Stop reference is the signal wick
  extreme. The default target is 2R.
- Stop is checked before target. If a single candle touches both, the backtest
  records a stop to avoid optimistic intrabar assumptions.
- If neither level is touched in the holding window, the trade closes at the
  final window close and is marked to market in R.
- Output is structured logging only. It submits no orders and does not model
  transaction costs or slippage.

### Rule checklist

- [ ] Use only closed candles and keep them in chronological order.
- [ ] Build higher-timeframe bars from source data without including a forming
      bar; record the bar-close/confirmation time for every fractal.
- [ ] Make higher-timeframe features available to a lower timeframe only after
      the higher-timeframe fractal is confirmed.
- [ ] Do not enter on the signal candle; use the next candle's open.
- [ ] Reject invalid risk (entry at or beyond stop) rather than manufacture a
      trade.
- [ ] Resolve same-candle stop/target ambiguity conservatively and consistently.
- [ ] Record expired trades at their actual window close.
- [ ] Add costs, slippage, and out-of-sample validation before interpreting
      performance as deployable.

CLI implementation: [`backtesting.py`](../../src/ict_scanner/ict/backtesting.py).

Implementation: [`backtesting.py`](../../src/ict_scanner/ict/backtesting.py).
