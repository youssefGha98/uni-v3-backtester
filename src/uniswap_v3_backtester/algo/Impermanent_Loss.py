
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel

from uniswap_v3_backtester.algo.math import compute_impermanent_loss, compute_realized_il


class ILTimeseries(BaseModel):
    timestamps: list[datetime]
    values: list[Decimal]


class ImpermanentLossTracker:
    def __init__(
        self,
        entry_tick: int,
        entry_token0: Decimal,
        entry_token1: Decimal,
        tick_lower: int,
        tick_upper: int,
    ):
        self.entry_tick = entry_tick
        self.entry_token0_ratio = (
            entry_token0 / (entry_token0 + entry_token1)
            if (entry_token0 + entry_token1) > 0
            else Decimal("0.5")
        )

        self.tick_lower = tick_lower
        self.tick_upper = tick_upper

        self.il_series: list[tuple[datetime, Decimal]] = []
        self.realized_il_series: list[tuple[datetime, Decimal]] = []

    def track_il(self, timestamp: datetime, current_tick: int) -> None:
        if current_tick < self.tick_lower:
            clamped_tick = self.tick_lower
        elif current_tick > self.tick_upper:
            clamped_tick = self.tick_upper
        else:
            clamped_tick = current_tick

        il = compute_impermanent_loss(
            current_tick=clamped_tick,
            entry_tick=self.entry_tick,
            min_tick=self.tick_lower,
            max_tick=self.tick_upper,
        )
        self.il_series.append((timestamp, il))

    def realize_il(
        self, timestamp: datetime, new_token0: Decimal, new_token1: Decimal
    ) -> None:
        current_ratio = (
            new_token0 / (new_token0 + new_token1)
            if (new_token0 + new_token1) > 0
            else Decimal("0.5")
        )
        target_ratio = self.entry_token0_ratio
        full_il = self.il_series[-1][1] if self.il_series else Decimal("0")

        realized = compute_realized_il(
            entry_token0_ratio=self.entry_token0_ratio,
            current_token0_ratio=current_ratio,
            target_token0_ratio=target_ratio,
            full_il=full_il,
        )
        self.realized_il_series.append((timestamp, realized))

    def get_il_series(self) -> ILTimeseries:
        ts, values = zip(*self.il_series) if self.il_series else ([], [])
        return ILTimeseries(timestamps=list(ts), values=list(values))

    def get_realized_il_series(self) -> ILTimeseries:
        ts, values = (
            zip(*self.realized_il_series) if self.realized_il_series else ([], [])
        )
        return ILTimeseries(timestamps=list(ts), values=list(values))

