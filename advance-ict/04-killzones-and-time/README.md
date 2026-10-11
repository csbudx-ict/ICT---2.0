# Killzones and Time

## Curriculum

### Multi-timeframe fractal workflow

Session liquidity and fractal structure should be recorded with their source
timeframe: Daily/4H for external dealing ranges, 1H/15M for intermediate
structure, and 5M for entry timing. Fractals must be confirmed by two later
closed bars from the same timeframe. The current live dashboard uses 5M
candles only; the higher-timeframe schedule below is not yet calculated as a
live multi-timeframe stack.

1. **Time context:** timestamp every candle with an explicit timezone and
   convert it to a single reference zone before session classification.
2. **Session ranges:** understand the Asian range as a source of reference
   highs/lows and subsequent session liquidity.
3. **Killzones:** focus analysis on selected London and New York AM windows;
   treat session timing as context rather than an independent signal.
4. **Session transitions:** record which configured window contains the
   signal candle so results can be segmented and reviewed.
5. **Calendar limitations:** distinguish fixed UTC windows from local exchange
   time, including daylight-saving shifts and holidays.

## Definitions and scanner rules

- **Killzone:** a configured time interval in which the scanner marks an
  entry window as active.
- **Asian:** 00:00–06:00 UTC. **London:** 07:00–10:00 UTC.
- **New York AM:** 12:00–15:00 UTC. **London Close:** 15:00–17:00 UTC.
- The current scanner marks London and New York AM as valid entry windows.
- Timestamps are converted to UTC before classification. Naive datetimes are
  rejected; ambiguous local timestamps must be localized correctly upstream.
- These are fixed UTC intervals, not DST-aware London/New York civil-time
  schedules. They will shift relative to those markets during parts of the
  year.

## Rule checklist

- [ ] Require timezone-aware timestamps at ingestion and in all ICT functions.
- [ ] Associate each session-range and fractal event with its source timeframe.
- [ ] Compare timestamps only after conversion to UTC; a higher-timeframe
      fractal is not confirmed until its two right-side bars close.
- [ ] Classify the timestamp of the signal's closed candle, not wall-clock
      render time.
- [ ] Store the session label with each backtest signal and dashboard snapshot.
- [ ] Apply the valid-window flag only as a confluence/filter where explicitly
      configured.
- [ ] Do not silently claim local London/New York accuracy from fixed UTC
      windows; account for DST if local-time scheduling is later required.

Implementation: [`killzones.py`](../../src/ict_scanner/ict/killzones.py) and
the live integration in [`engine.py`](../../src/ict_scanner/ict/engine.py).
