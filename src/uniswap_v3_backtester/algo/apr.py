from datetime import datetime
from decimal import Decimal, getcontext
from collections import defaultdict
from typing import List, Tuple, Dict
from pydantic import BaseModel

from uniswap_v3_backtester.algo.math import sqrtPriceX96_to_price_adjusted, tick_to_price

getcontext().prec = 40  # High precision

class APRTimeseries(BaseModel):
    dates: List[datetime]
    aprs: List[Decimal]


class APRTracker:
    def __init__(
        self,
        initial_token0: Decimal,
        initial_token1: Decimal,
        initial_tick: int,
        token0_decimals: int = 8,
        token1_decimals: int = 18,
    ):
        self.initial_token0_scaled = self._scale(initial_token0, token0_decimals)
        self.initial_token1_scaled = self._scale(initial_token1, token1_decimals)
        self.initial_tick = initial_tick
        self.token0_decimals = token0_decimals
        self.token1_decimals = token1_decimals

        self.start_date: datetime | None = None
        self.end_states_by_day: Dict[datetime, Tuple[Decimal, Decimal, Decimal, Decimal, int]] = {}

    def _scale(self, amount: Decimal, decimals: int) -> Decimal:
        return amount / Decimal(10 ** decimals)


    def track(
        self,
        timestamp: datetime,
        token0: Decimal,
        token1: Decimal,
        fee_token0: Decimal,
        fee_token1: Decimal,
        sqrtPriceX96: int,
    ) -> None:
        day = datetime(timestamp.year, timestamp.month, timestamp.day)
        if self.start_date is None:
            self.start_date = day

        t0 = self._scale(token0, self.token0_decimals)
        t1 = self._scale(token1, self.token1_decimals)
        f0 = self._scale(fee_token0, self.token0_decimals)
        f1 = self._scale(fee_token1, self.token1_decimals)
        self.end_states_by_day[day] = (t0, t1, f0, f1, sqrtPriceX96)

    def compute_apr_on_dates(self, query_dates: List[datetime]) -> APRTimeseries:
        if self.start_date is None:
            return APRTimeseries(dates=[], aprs=[])

        aprs = []
        dates = []

        for query_date in query_dates:
            if query_date <= self.start_date:
                continue

            valid_days = [d for d in self.end_states_by_day.keys() if d <= query_date]
            if not valid_days:
                continue

            last_day = max(valid_days)
            token0, token1, fee0, fee1, sqrtPriceX96 = self.end_states_by_day[last_day]

            # Adjusted price (token1 per token0)
            price_token1_per_token0 = sqrtPriceX96_to_price_adjusted(
                sqrtPriceX96,
                token0_decimals=self.token0_decimals,
                token1_decimals=self.token1_decimals
            )

            # LP value in token1
            total_token0 = token0 + fee0
            total_token1 = token1 + fee1
            token0_value_in_token1 = total_token0 * price_token1_per_token0
            lp_value_token1 = total_token1 + token0_value_in_token1

            # HODL benchmark
            initial_token0_value_in_token1 = self.initial_token0_scaled * price_token1_per_token0
            hodl_value_token1 = self.initial_token1_scaled + initial_token0_value_in_token1

            # APR calculation
            net_gain = lp_value_token1 - hodl_value_token1
            days_elapsed = (query_date - self.start_date).days
            if days_elapsed < 1:
                continue
            apr = (net_gain / hodl_value_token1) * 100
            dates.append(query_date)
            aprs.append(apr)

        return APRTimeseries(dates=dates, aprs=aprs)
