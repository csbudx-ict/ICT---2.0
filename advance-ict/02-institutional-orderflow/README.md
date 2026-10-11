# Institutional Orderflow

## Curriculum

### Multi-timeframe fractal workflow

Use Daily/4H fractals to frame external structure, 1H/15M fractals to refine
internal structure and displacement context, and 5M for entry timing. This is
the study model, not a claim that the current live scanner calculates every
timeframe: current dashboard and scheduler scans use 5M data.

Each timeframe has its own five-bar fractal pivots (two bars on each side).
A pivot becomes usable after the two right-side candles of that timeframe have
closed. Structure breaks, order-block origins, mitigation, and breaker
invalidation must be timestamp-ordered using only then-available candles.

1. **Displacement and structure:** distinguish a meaningful close beyond a
   recent range from a wick-only probe. A Market Structure Shift (MSS) is a
   directional break of a confirmed swing with sufficient displacement.
2. **Order blocks:** the last candle closing against the impulse immediately
   before the directional displacement; treat its range as a candidate
   reaction zone.
3. **Mitigation:** price revisits an unmitigated candidate block after the
   displacement. The 50% Mean Threshold (MT) is the midpoint of the source
   candle's high-low range.
4. **Breaker blocks:** an order block is invalidated by a later close through
   its far boundary; it may then act as a zone in the opposite direction.
5. **Rejection blocks:** a long rejection wick at a liquidity sweep can define
   a narrow candidate zone when the sweep candle closes back from the extreme.

## Definitions and scanner rules

- **Displacement:** an impulse candle range/body compared with recent average
  range; the scanner applies its configured threshold.
- **Bullish order block:** last bearish candle before a qualifying bullish
  impulse. **Bearish order block:** last bullish candle before a qualifying
  bearish impulse.
- **Mitigation block (scanner definition):** qualifying displacement closes
  beyond the preceding range; the most recent opposing source candle defines
  the zone; a subsequent closed candle must overlap the zone and close on the
  displacement side of its MT.
- **Breaker:** a SELL-side block becomes bullish after a later close above its
  high; a BUY-side block becomes bearish after a later close below its low.
- **Rejection block (scanner definition):** only considered when the latest
  closed candle is also a detected Turtle Soup sweep. Its directional wick must
  be at least 1.5 times its body (using a small body floor).

## Rule checklist

- [ ] Confirm displacement and structure break with closed candles, not wicks
      alone.
- [ ] Do not promote a lower-timeframe structure break to a higher-timeframe
      MSS without a separately confirmed higher-timeframe fractal.
- [ ] Wait for both right-side bars before treating a fractal as confirmed.
- [ ] Keep the source candle, impulse, and retest timestamps in chronological
      order.
- [ ] Calculate MT as `(source high + source low) / 2`.
- [ ] Do not call an ordinary order-block retest a mitigation signal unless the
      configured retest and close conditions pass.
- [ ] Flip breaker direction only after a close beyond the source block.
- [ ] Treat all blocks as candidate zones; require independent context and risk
      validation before trading.

Implementation: [`order_blocks.py`](../../src/ict_scanner/ict/order_blocks.py),
[`breaker_blocks.py`](../../src/ict_scanner/ict/breaker_blocks.py),
[`institutional_order_block.py`](../../src/ict_scanner/ict/institutional_order_block.py),
and [`advance_ict.py`](../../src/ict_scanner/ict/advance_ict.py).
