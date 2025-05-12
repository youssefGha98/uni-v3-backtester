from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel



class Pool(BaseModel):
    address: str
    token0: str
    token1: str
    fee: Decimal


class Position(BaseModel):
    tick_lower: int
    tick_upper: int
    amount0: Decimal
    amount1: Decimal
    pool: Pool
    liquidity: Decimal


class Swap(BaseModel):
    tick: int
    volume_token0: Decimal
    volume_token1: Decimal
    liquidity: Decimal
    timestamp: datetime
    sqrt_price_x96: int


class SwapSeries(BaseModel):
    swaps: list[Swap]

    @property
    def ticks(self) -> list[int]:
        return [s.tick for s in self.swaps]

    @property
    def timestamps(self) -> list[datetime]:
        return [s.timestamp for s in self.swaps]
