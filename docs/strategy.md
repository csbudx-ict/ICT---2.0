# ICT strategy calculations

The strategy helpers operate on closed, timezone-aware candles and are deterministic. The
`/live-demo` feed is synthetic and accelerated; it is for exercising detector wiring only and is
not market data or a trading recommendation.

## Dashboard detectors

- **FVG:** a three-candle imbalance. Bullish gaps are between candle 1's high and candle 3's low;
  bearish gaps are between candle 3's high and candle 1's low. A gap is fully mitigated only after
  a later closed candle trades through its far edge.
- **Order block:** the last opposite-colored candle before the displacement candle.
- **OTE Fibonacci:** the 0.618–0.790 retracement of the selected dealing range; 0.705 is exposed as
  the sweet spot. Bullish retracements are measured down from the high, bearish retracements up from
  the low.
- **Breaker block:** an order block becomes a bullish breaker after a later candle closes above its
  high, or a bearish breaker after a later candle closes below its low. The original block bounds
  are retained as the breaker zone.
- **Premium / Discount:** the dealing range is split at its 50% equilibrium. Prices below are
  Discount, above are Premium, and the exact midpoint is Equilibrium. Long entries must be below
  equilibrium; short entries must be above it.
- **BOX / Liquidity:** the detector takes a configurable closed-candle range (12 bars by default),
  requires the range to be compact relative to its average true range, and checks the newest candle
  for a wick through a box boundary that closes back inside. It also reports confirmed five-bar
  swing pools, equal highs/lows, prior-day/week highs/lows, and the current day's Asian high/low.
  The newest candle does not change the box boundaries.
- **Master Sniper:** a strict confluence gate requiring a same-direction FVG, overlapping order
  block, OTE entry, matching breaker, aligned Premium/Discount entry, matching box and swing/equal
  liquidity sweep, displacement MSS, and a London or New York AM killzone. Disabling any of the six
  core dashboard detectors prevents the master signal from being marked ready.
- **Unicorn Setup:** the latest completed three-candle FVG must align with an MSS displacement on
  its middle candle and overlap or touch a previously formed, same-direction breaker block. The
  signal reports both zones, the MSS level, and their timestamps.
- **Silver Bullet FVG:** checks only the latest three closed candles. A bullish gap is candle 1's
  high to candle 3's low; a bearish gap is candle 3's high to candle 1's low. It reports ordered
  zone bounds, proximal/distal boundaries, and the 50% retracement entry. No session-time filter is
  applied by this FVG detector.
- **Institutional Order Block:** requires a latest-candle MSS with displacement meeting the
  configured ATR multiplier, then selects the last opposing candle before that impulse. Its 50%
  candle-range midpoint is exposed as the mean threshold and mitigation entry.

The dashboard sends a configure message over its WebSocket when module switches change. Detector
values are sent only for enabled switches. Signals may be absent when the current candle window
does not match that detector's rules.
# Live dashboard data and model selection

The main dashboard connects to `/api/ws/dashboard`. The endpoint reads active pairs
and provider assignments from the scanner database, then requests closed 5-minute
candles from each configured provider. It does not fall back to synthetic candles.
Pairs without an available provider feed or required credentials are shown as
unavailable with a reason.

The market lab at `/live-demo` polls Twelve Data's one-minute time-series endpoint for EUR/USD,
GBP/USD, and XAU/USD, then pushes the latest completed candles and seven selected ICT modules over
the application's `/api/ws/live-market` WebSocket. The prior `/api/ws/demo/eurusd` route remains as
a compatibility alias and now streams the same live provider data. The API key is loaded from
`TWELVE_DATA_API_KEY` in `.env` and is never sent to the browser. Current/incomplete interval
candles are filtered by UTC timestamp before conversion to domain candles. Polling defaults to once
per minute (configurable with `TWELVE_DATA_POLL_INTERVAL_SECONDS`) to avoid continuously spending
API credits; Twelve Data plan entitlements and quotas determine actual availability. A missing key
or provider response is reported as unavailable; no synthetic candles are substituted. Changing
module selections immediately recalculates cached closed candles without issuing an extra provider
request.

The Fibonacci level array is `[0, 1, 0.618, 0.705, 0.79, -1, -0.62, -0.27, 0.5]`.
OTE is the 0.618–0.79 retracement zone, with 0.705 as the sweet spot. The dashboard
only analyzes provider-returned closed candles; it does not synthesize missing data.
