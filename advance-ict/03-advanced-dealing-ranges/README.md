# Advanced Dealing Ranges

## Curriculum

### Multi-timeframe fractal workflow

Anchor a higher-timeframe dealing range from confirmed Daily/4H swing
fractals, refine with 1H/15M structure, then use 5M arrays for entry context.
These are separate timeframe candle series; each fractal requires two later
closed bars on its own timeframe. This framework is curriculum guidance:
current live scanner snapshots calculate the listed arrays from 5M candles
only, without higher-timeframe range aggregation.

1. **Dealing range:** define a meaningful swing low/high and its 50%
   equilibrium (EQ).
2. **Premium and discount:** prices above EQ are premium; prices below EQ are
   discount. EQ itself is a separate neutral zone.
3. **OTE retracement:** map a completed directional impulse and identify the
   0.618–0.790 retracement area, with 0.705 as the sweet-spot reference.
4. **PD arrays:** compare candidate FVG, order-block, breaker, and OTE zones
   with the dealing-range equilibrium and directional bias.
5. **Confluence:** use range location as context for a setup, not as a trigger
   by itself.

## Definitions and scanner rules

- **Equilibrium:** `(range low + range high) / 2`.
- **Discount:** price below equilibrium. **Premium:** price above equilibrium.
- **Bullish OTE:** retracement levels measured down from the impulse high;
  **bearish OTE:** retracement levels measured up from the impulse low.
- The configured Fibonacci array is `[0, 1, 0.618, 0.705, 0.79, -1, -0.62,
  -0.27, 0.5]`. The `-1`, `-0.62`, and `-0.27` values are extension references
  under the scanner's signed ratio convention.
- A PD array is emitted only when its bounds are numeric and valid; its midpoint
  is labeled DISCOUNT, EQUILIBRIUM, or PREMIUM against the active range.
- BUY alignment requires a zone midpoint in discount; SELL alignment requires
  a midpoint in premium. Equilibrium is not counted as either.
- Live calculations use the current closed-candle range window; they do not
  include an unfinished candle.

## Rule checklist

- [ ] Validate that range prices are finite and `high > low`.
- [ ] Anchor multi-timeframe ranges to confirmed pivots on the timeframe whose
      range is being measured; do not substitute a 5M pivot for a 4H anchor.
- [ ] Use no fractal before its two right-side candles have closed.
- [ ] Set and document the impulse anchors before calculating retracements.
- [ ] Keep bullish and bearish fib direction conventions distinct.
- [ ] Highlight 0.705 without treating it as a guaranteed reversal price.
- [ ] Classify each array midpoint against the same active EQ.
- [ ] Prefer directional premium/discount alignment as confluence; never infer
      entry, stop, or target from range location alone.

Implementation: [`fibonacci.py`](../../src/ict_scanner/ict/fibonacci.py),
[`premium_discount.py`](../../src/ict_scanner/ict/premium_discount.py), and
[`advance_ict.py`](../../src/ict_scanner/ict/advance_ict.py).
