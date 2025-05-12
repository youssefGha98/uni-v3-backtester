
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from uniswap_v3_backtester.algo.math import compute_token_amounts_from_liquidity
from uniswap_v3_backtester.algo.pool import Position, Swap


class ActivityTimeseries(BaseModel):
    timestamps: list[datetime]
    activity: list[bool]


class ActivityTracker(BaseModel):
    position: Position
    timestamps: list[datetime] = []
    activity: list[bool] = []
    amounts_token0: list[Decimal] = []
    amounts_token1: list[Decimal] = []

    def is_active(self, tick: int) -> bool:
        return self.position.tick_lower <= tick <= self.position.tick_upper

    def track(self, swap: Swap) -> None:
        active = self.is_active(swap.tick)
        amount0, amount1 = compute_token_amounts_from_liquidity(
            self.position.tick_lower,
            self.position.tick_upper,
            self.position.liquidity,
            swap.tick,
        )
        self.position.amount0 = amount0
        self.position.amount1 = amount1

        self.amounts_token0.append(amount0)
        self.amounts_token1.append(amount1)
        self.timestamps.append(swap.timestamp)
        self.activity.append(active)

    def get_timeseries(self) -> ActivityTimeseries:
        return ActivityTimeseries(
            timestamps=self.timestamps,
            activity=self.activity,
        )
