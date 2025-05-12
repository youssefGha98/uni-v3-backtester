from datetime import datetime
from decimal import Decimal

import pytest

from uniswap_v3_backtester.algo.activity import ActivityTracker
from uniswap_v3_backtester.algo.math import compute_token_amounts_from_liquidity
from uniswap_v3_backtester.algo.pool import Swap, SwapSeries


def test_is_active_boundaries(position):
    tracker = ActivityTracker(position=position)
    assert tracker.is_active(1000)
    assert tracker.is_active(1500)
    assert tracker.is_active(2000)


def test_is_active_outside(position):
    tracker = ActivityTracker(position=position)
    assert not tracker.is_active(999)
    assert not tracker.is_active(2001)


def test_track_timeseries(position, swap_series):
    tracker = ActivityTracker(position=position)

    for swap in swap_series.swaps:
        tracker.track(swap)

    timeseries = tracker.get_timeseries()

    expected = [
        False,  # tick = 950
        True,  # tick = 1500
        False,  # tick = 2100
    ]

    assert timeseries.activity == expected
    assert timeseries.timestamps == swap_series.timestamps


def test_track_empty_series(position):
    tracker = ActivityTracker(position=position)
    empty_series = SwapSeries(swaps=[])

    for swap in empty_series.swaps:
        tracker.track(swap)

    result = tracker.get_timeseries()
    assert result.activity == []
    assert result.timestamps == []


def test_is_active_after_rebalance_still_active(position):
    tracker = ActivityTracker(position=position)

    assert tracker.is_active(1500)

    position.tick_lower = 1400
    position.tick_upper = 1600
    assert tracker.is_active(1500)


def test_is_active_after_rebalance_becomes_inactive(position):
    tracker = ActivityTracker(position=position)

    assert tracker.is_active(1500)

    position.tick_lower = 1600
    position.tick_upper = 1800
    assert not tracker.is_active(1500)


def test_inactive_becomes_active_after_rebalance(position):
    tracker = ActivityTracker(position=position)
    assert not tracker.is_active(900)

    position.tick_lower = 800
    position.tick_upper = 950
    assert tracker.is_active(900)


def test_inactive_remains_inactive_after_rebalance(position):
    tracker = ActivityTracker(position=position)
    assert not tracker.is_active(3000)

    position.tick_lower = 100
    position.tick_upper = 200
    assert not tracker.is_active(3000)


@pytest.mark.parametrize(
    "tick, expected_range",
    [
        (950, "below"),  # below range
        (1500, "in"),  # in range
        (2100, "above"),  # above range
    ],
)
def test_tracker_updates_position_amounts_by_range(position, tick, expected_range):
    tracker = ActivityTracker(position=position)
    swap = Swap(
        tick=tick,
        volume_token0=Decimal("100"),
        volume_token1=Decimal("200"),
        liquidity=Decimal("10000"),
        sqrt_price_x96=100,
        timestamp=datetime.utcnow(),
    )

    tracker.track(swap)

    expected_amount0, expected_amount1 = compute_token_amounts_from_liquidity(
        tick_lower=position.tick_lower,
        tick_upper=position.tick_upper,
        liquidity=position.liquidity,
        current_tick=tick,
    )

    assert position.amount0 == pytest.approx(expected_amount0, abs=1e-8)
    assert position.amount1 == pytest.approx(expected_amount1, 1e-8)

    assert tracker.amounts_token0[-1] == pytest.approx(expected_amount0, abs=1e-8)
    assert tracker.amounts_token1[-1] == pytest.approx(expected_amount1, abs=1e-8)
