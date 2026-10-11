from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from math import isfinite
from pathlib import Path

import structlog

import pandas as pd
from ict_scanner.domain.enums import Direction
from ict_scanner.domain.models import Candle
from ict_scanner.ict.advance_ict import detect_turtle_soup

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class BacktestTrade:
    signal_time: str
    entry_time: str
    direction: Direction
    entry: float
    stop: float
    target: float
    result_r: float


@dataclass(frozen=True)
class BacktestSummary:
    trades: tuple[BacktestTrade, ...]
    wins: int
    losses: int
    expired: int
    win_rate: float
    expectancy_r: float


def backtest_turtle_soup(
    candles: Sequence[Candle],
    *,
    reward_to_risk: float = 2.0,
    max_holding_candles: int = 24,
) -> BacktestSummary:
    """Walk forward over closed candles, entering no earlier than the next candle.

    When one candle reaches both stop and target, the stop is counted first. Trades
    that do not reach either level within the holding window are closed at its last
    close and measured in R, avoiding optimistic result assumptions.
    """
    if not isfinite(reward_to_risk) or reward_to_risk <= 0:
        raise ValueError("reward_to_risk must be finite and positive")
    if max_holding_candles < 1:
        raise ValueError("max_holding_candles must be at least 1")
    trades: list[BacktestTrade] = []
    index = 3
    while index < len(candles) - 1:
        signal = detect_turtle_soup(candles[: index + 1])
        if signal is None:
            index += 1
            continue
        direction_value = signal.get("direction")
        stop_value = signal.get("stop_reference")
        if direction_value not in (Direction.BUY.value, Direction.SELL.value) or not isinstance(
            stop_value, (int, float)
        ):
            index += 1
            continue

        direction = Direction(str(direction_value))
        entry_index = index + 1
        entry = candles[entry_index].open
        stop = float(stop_value)
        risk = entry - stop if direction is Direction.BUY else stop - entry
        if risk <= 0:
            index += 1
            continue
        target = entry + risk * reward_to_risk if direction is Direction.BUY else entry - risk * reward_to_risk
        expiry_index = min(len(candles) - 1, entry_index + max_holding_candles - 1)
        result_r = 0.0
        resolved = False
        for future in candles[entry_index : expiry_index + 1]:
            if direction is Direction.BUY:
                stop_hit = future.low <= stop
                target_hit = future.high >= target
            else:
                stop_hit = future.high >= stop
                target_hit = future.low <= target
            if stop_hit:
                result_r = -1.0
                resolved = True
                break
            if target_hit:
                result_r = reward_to_risk
                resolved = True
                break
        if not resolved:
            close = candles[expiry_index].close
            result_r = (close - entry) / risk if direction is Direction.BUY else (entry - close) / risk
        trades.append(
            BacktestTrade(
                signal_time=str(signal["timestamp"]),
                entry_time=candles[entry_index].timestamp.isoformat(),
                direction=direction,
                entry=entry,
                stop=stop,
                target=target,
                result_r=result_r,
            )
        )
        index = expiry_index + 1

    wins = sum(trade.result_r > 0 for trade in trades)
    losses = sum(trade.result_r < 0 for trade in trades)
    expired = len(trades) - wins - losses
    return BacktestSummary(
        trades=tuple(trades),
        wins=wins,
        losses=losses,
        expired=expired,
        win_rate=wins / len(trades) if trades else 0.0,
        expectancy_r=sum(trade.result_r for trade in trades) / len(trades) if trades else 0.0,
    )


def _load_csv(path: Path) -> list[Candle]:
    frame = pd.read_csv(path)
    required = {"timestamp", "open", "high", "low", "close"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"CSV is missing required columns: {', '.join(sorted(missing))}")
    timestamps = pd.to_datetime(frame["timestamp"], utc=True, errors="raise")
    volumes = frame["volume"] if "volume" in frame else pd.Series(0.0, index=frame.index)
    return [
        Candle(
            timestamp=timestamp.to_pydatetime(),
            open=float(row.open),
            high=float(row.high),
            low=float(row.low),
            close=float(row.close),
            volume=float(volume),
        )
        for timestamp, row, volume in zip(timestamps, frame.itertuples(), volumes, strict=True)
    ]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Walk-forward Turtle Soup backtest for closed candles.")
    parser.add_argument("csv", type=Path, help="CSV with timestamp,open,high,low,close[,volume] columns")
    parser.add_argument("--reward-to-risk", type=float, default=2.0)
    parser.add_argument("--max-holding-candles", type=int, default=24)
    arguments = parser.parse_args(argv)
    if not arguments.csv.is_file():
        parser.error(f"CSV does not exist: {arguments.csv}")

    candles = _load_csv(arguments.csv)
    summary = backtest_turtle_soup(
        candles,
        reward_to_risk=arguments.reward_to_risk,
        max_holding_candles=arguments.max_holding_candles,
    )
    logger.info(
        "turtle_soup_backtest_complete",
        input=str(arguments.csv),
        candles=len(candles),
        trades=len(summary.trades),
        wins=summary.wins,
        losses=summary.losses,
        expired=summary.expired,
        win_rate=summary.win_rate,
        expectancy_r=summary.expectancy_r,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
