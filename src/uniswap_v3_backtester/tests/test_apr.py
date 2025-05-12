from datetime import datetime, timedelta
from decimal import Decimal
from uniswap_v3_backtester.algo.apr import APRTracker
import pytest

def test_apr_tracker_with_il_adjustment():
    initial_token0 = Decimal("100")
    initial_token1 = Decimal("0")
    initial_tick = 0  # price = 1.0

    tracker = APRTracker(
        initial_token0=initial_token0,
        initial_token1=initial_token1,
        initial_tick=initial_tick,
    )

    timestamp1 = datetime(2024, 1, 1)
    timestamp2 = datetime(2024, 1, 2)
    timestamp3 = datetime(2024, 1, 3)
    tick = 0  # price = 1.0

    tracker.track(timestamp1, fee_token0=Decimal("1"), fee_token1=Decimal("0"), current_tick=tick)  # $1
    tracker.track(timestamp2, fee_token0=Decimal("1"), fee_token1=Decimal("0"), current_tick=tick)  # $1

    tracker.set_il_series([
        (timestamp3, Decimal("0.01"))  # 1%
    ])

    # Create tick context (unchanged)
    tick_context = {
        timestamp1: tick,
        timestamp2: tick,
        timestamp3: tick,
    }

    # Query APR on day 3
    apr_result = tracker.compute_apr_on_dates(
        query_dates=[timestamp3],
        tick_context=tick_context,
    )

    # Expected:
    # - Initial value: $100
    # - Fees: $2
    # - IL loss: $1
    # - Net gain = $1
    # - Duration = 2 days => APR = 1/100 * 365/2 = 1.825 = 182.5%

    assert len(apr_result.aprs) == 1
    computed_apr = apr_result.aprs[0]
    print(apr_result.aprs[0])

    assert computed_apr == pytest.approx(Decimal("182.5") , abs=1e-2)


