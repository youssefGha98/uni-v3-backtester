

from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel

from uniswap_v3_backtester.algo.pool import Position, Swap


class Fee(BaseModel):
    token0: Decimal
    token1: Decimal


class FeeTimeseries(BaseModel):
    timestamps: list[datetime]
    fees: list[Fee]


class FeeCalculator(BaseModel):
    position: Position
    _timestamps: list[datetime] = []
    _fees: list[Fee] = []
    _total_fee: Fee = Fee(token0=Decimal(0), token1=Decimal(0))

    def compute_fee_for_swap(self, swap: Swap) -> Fee:
        total_liquidity = swap.liquidity + self.position.liquidity
        liq_share = self.position.liquidity / total_liquidity

        if swap.volume_token0 > 0 and swap.volume_token1 < 0:
            total_fee_0 = swap.volume_token0 * self.position.pool.fee
            return Fee(
                token0=liq_share * total_fee_0,
                token1=Decimal(0),
            )
        elif swap.volume_token1 > 0 and swap.volume_token0 < 0:
            total_fee_1 = swap.volume_token1 * self.position.pool.fee
            return Fee(
                token0=Decimal(0),
                token1=liq_share * total_fee_1,
            )
        else:
            return Fee(token0=Decimal(0), token1=Decimal(0))

    def track(self, swap: Swap, is_active: bool) -> None:
        fee = self.compute_fee_for_swap(swap)
        if is_active:
            self._timestamps.append(swap.timestamp)
            self._fees.append(fee)
            self._total_fee.token0 += fee.token0
            self._total_fee.token1 += fee.token1
        else:
            self._timestamps.append(swap.timestamp)
            self._fees.append(Fee(token0=Decimal(0), token1=Decimal(0)))

    def get_timeseries(self) -> FeeTimeseries:
        return FeeTimeseries(
            timestamps=self._timestamps,
            fees=self._fees,
        )

    def get_total_fees(self) -> Fee:
        return self._total_fee