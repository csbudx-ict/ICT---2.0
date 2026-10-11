# Liquidity Engineering

## Curriculum

### Multi-timeframe fractal workflow

Study external liquidity on Daily/4H, refine structure and internal pools on
1H/15M, and use 5M for entry timing. This is the curriculum workflow; current
live scanner snapshots analyze 5M candles only and do not yet compute this full
timeframe stack.

A fractal swing is a five-bar pivot: its high/low exceeds the two bars before
and the two bars after it. It is confirmed only when both right-hand candles
have closed. Confirm each timeframe independently and never use an unconfirmed
pivot or future candle to label a past signal.

1. **Liquidity pools:** resting orders are commonly discussed around obvious
   swing points and repeated highs/lows. The scanner classifies buy-side
   liquidity (BSL) above highs and sell-side liquidity (SSL) below lows.
2. **Pool types:** confirmed swing highs/lows, equal highs/lows (EQH/EQL), prior
   day/week highs/lows (PDH/PDL, PWH/PWL), and the Asian session range.
3. **Inducement:** a candidate internal swing that may attract price before a
   move toward a larger external pool. It is a contextual candidate, not proof
   that orders are present.
4. **Liquidity sweep / Turtle Soup:** price trades through a previously formed
   pool and the same closed candle reclaims it, suggesting rejection rather
   than acceptance beyond that level.

## Definitions and scanner rules

- **BSL:** liquidity reference above a high; **SSL:** reference below a low.
- **Confirmed swing:** a local high/low with two neighboring closed candles on
  each side. A swing is only usable after its right-side candles close.
- **Equal pool:** two or more highs/lows within the configured price tolerance.
- **Inducement candidate:** the latest confirmed internal swing opposing the
  chosen direction. BUY context uses an SSL swing; SELL context uses a BSL
  swing. The final candle is not accepted as a swing pivot.
- **Turtle Soup:** for BSL, the trigger candle's high exceeds an earlier pool
  and its close finishes below that pool; for SSL, its low breaks the pool and
  its close finishes above. The trigger candle is excluded from pool creation.
- **Sweep extreme:** the wick extreme of the reclaim candle; the detector
  exposes it as a stop reference, not a recommended order.

## Rule checklist

- [ ] Use timezone-aware candle timestamps.
- [ ] Keep higher-timeframe external pools distinct from lower-timeframe
      inducement/fractal pools.
- [ ] Confirm each timeframe's five-bar fractals only after two right-side
      candles from that same timeframe close.
- [ ] Form pools using only candles that closed before the candidate sweep.
- [ ] Require an actual wick through the pool and a close back across it.
- [ ] Keep BSL sweeps bearish and SSL sweeps bullish in directional labeling.
- [ ] Record pool source, price, trigger time, and wick extreme for review.
- [ ] Do not interpret an inducement candidate or a single sweep as confirmation
      of a complete trade setup.

Implementation: [`liquidity.py`](../../src/ict_scanner/ict/liquidity.py) and
[`advance_ict.py`](../../src/ict_scanner/ict/advance_ict.py).
