from datetime import datetime
from decimal import Decimal

from uniswap_v3_backtester.algo.fees import FeeCalculator
from uniswap_v3_backtester.algo.pool import Position, Swap, SwapSeries


def make_test_swap(tick: int) -> Swap:
    return Swap(
        tick=tick,
        volume_token0=Decimal("100"),
        volume_token1=Decimal("200"),
        liquidity=Decimal("10000"),
        sqrt_price_x96=10000,
        timestamp=datetime.now(),
    )



def test_compute_fee_for_swap_zero_position_liquidity(pool):
    position = Position(
        tick_lower=1000,
        tick_upper=2000,
        amount0=Decimal("0"),
        amount1=Decimal("0"),
        pool=pool,
        liquidity=Decimal("0"),
    )

    swap = make_test_swap(1500)

    calc = FeeCalculator(position=position)
    fee = calc.compute_fee_for_swap(swap)
    assert fee.token0 == Decimal("0")
    assert fee.token1 == Decimal("0")


def test_track_fee_timeseries(position, swap_series):
    calc = FeeCalculator(position=position)

    for swap in swap_series.swaps:
        calc.track(swap, is_active=True)

    result = calc.get_timeseries()
    assert len(result.fees) == len(swap_series.swaps)
    assert len(result.fees) == len(result.timestamps)
    assert set(result.timestamps) == set(swap_series.timestamps)


def test_track_fee_timeseries_empty(position):
    empty_series = SwapSeries(swaps=[])
    calc = FeeCalculator(position=position)

    for swap in empty_series.swaps:
        calc.track(swap, is_active=True)

    result = calc.get_timeseries()
    assert result.fees == []
    assert result.timestamps == []

def test_fee_not_collected_when_becomes_inactive_after_rebalance(position):
    calc = FeeCalculator(position=position)
    swap = make_test_swap(1500)

    position.tick_lower = 1600
    position.tick_upper = 1800
    calc.track(swap, is_active=False)
    total = calc.get_total_fees()
    assert total.token0 == 0
    assert total.token1 == 0


def test_fee_not_collected_when_still_inactive_after_rebalance(position):
    calc = FeeCalculator(position=position)
    swap = make_test_swap(3000)

    position.tick_lower = 100
    position.tick_upper = 200
    calc.track(swap, is_active=False)
    total = calc.get_total_fees()
    assert total.token0 == 0
    assert total.token1 == 0
