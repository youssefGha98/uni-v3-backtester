from datetime import datetime, timedelta

import pytest

from uniswap_v3_backtester.algo.rebalancer import (
    LogicMode,
    MultiConditionRebalancer,
    OutOfRangeDurationRebalancer,
    OutOfRangeRebalancer,
    RebalancerContext,
    RebalancingStrategy,
    TimeTriggeredRebalancer,
    compute_tick_range,
)

now = datetime.now()


def make_context(tick, timestamp, lower, upper, created_at=now):
    return RebalancerContext(
        tick=tick,
        timestamp=timestamp,
        tick_lower=lower,
        tick_upper=upper,
        created_at=created_at,
    )


def test_tick_range_with_bias():
    center = 1500
    width = 100
    lower, upper = compute_tick_range(center, width, bias=0.25)
    assert lower == 1475 and upper == 1575


def test_bias_validation_failure():
    strat = TimeTriggeredRebalancer(interval=timedelta(minutes=1))
    ctx = make_context(1500, now, 1400, 1600)
    with pytest.raises(ValueError):
        strat.rebalance(ctx, -0.1)
    with pytest.raises(ValueError):
        strat.rebalance(ctx, 1.1)


def test_base_strategy_interface():
    class DummyStrategy(RebalancingStrategy):
        pass

    strat = DummyStrategy()
    ctx = make_context(1500, now, 1000, 2000)
    with pytest.raises(NotImplementedError):
        strat.should_rebalance(ctx)
    with pytest.raises(NotImplementedError):
        strat.rebalance(ctx, 0.5)


def test_time_triggered_rebalance(position):
    strat = TimeTriggeredRebalancer(interval=timedelta(minutes=1))
    lower, upper = position.tick_lower, position.tick_upper

    ts1 = now
    ts2 = ts1 + timedelta(minutes=2)

    ctx1 = make_context(1500, ts1, lower, upper)
    ctx2 = make_context(1500, ts2, lower, upper)

    assert not strat.should_rebalance(ctx1)
    strat.rebalance(ctx1, 0.5)
    assert not strat.should_rebalance(
        make_context(1500, ts1 + timedelta(minutes=1), lower, upper)
    )
    assert strat.should_rebalance(ctx2)


def test_out_of_range_rebalancer(position):
    strat = OutOfRangeRebalancer()
    lower, upper = position.tick_lower, position.tick_upper

    assert strat.should_rebalance(make_context(950, now, lower, upper))
    assert not strat.should_rebalance(make_context(1500, now, lower, upper))
    assert strat.should_rebalance(make_context(2100, now, lower, upper))

    new_lower, new_upper = strat.rebalance(make_context(2100, now, lower, upper), 0.5)
    assert new_lower != lower and new_upper != upper


def test_out_of_range_duration_rebalancer(position):
    strat = OutOfRangeDurationRebalancer(duration=timedelta(seconds=30))
    lower, upper = position.tick_lower, position.tick_upper

    t0 = now
    t1 = now + timedelta(seconds=20)
    t2 = now + timedelta(seconds=40)

    assert not strat.should_rebalance(make_context(950, t0, lower, upper))
    assert not strat.should_rebalance(make_context(1500, t1, lower, upper))
    assert strat.should_rebalance(make_context(2100, t2, lower, upper))


def test_multi_condition_or_mode(position):
    strat = MultiConditionRebalancer(
        strategies=[
            OutOfRangeRebalancer(),
            TimeTriggeredRebalancer(interval=timedelta(seconds=0)),
        ],
        mode=LogicMode.OR,
    )
    ctx = make_context(950, now, position.tick_lower, position.tick_upper)
    assert strat.should_rebalance(ctx)


def test_multi_condition_and_mode(position):
    ttr = TimeTriggeredRebalancer(interval=timedelta(seconds=0))
    strat = MultiConditionRebalancer(
        strategies=[OutOfRangeRebalancer(), ttr],
        mode=LogicMode.AND,
    )
    ctx_rebalance = make_context(950, now, position.tick_lower, position.tick_upper)
    ttr.rebalance(ctx_rebalance, 0.5)

    ctx_check = make_context(
        1500, now + timedelta(seconds=1), position.tick_lower, position.tick_upper
    )
    assert not strat.should_rebalance(ctx_check)


def test_time_triggered_negative_interval():
    with pytest.raises(ValueError):
        TimeTriggeredRebalancer(interval=timedelta(seconds=-1))


def test_time_triggered_exact_same_timestamp(position):
    strat = TimeTriggeredRebalancer(interval=timedelta(seconds=60))
    ctx = make_context(1500, now, position.tick_lower, position.tick_upper)
    strat.rebalance(ctx, 0.5)
    assert not strat.should_rebalance(ctx)


def test_out_of_range_edge_ticks(position):
    strat = OutOfRangeRebalancer()
    lower, upper = position.tick_lower, position.tick_upper
    assert not strat.should_rebalance(make_context(lower, now, lower, upper))
    assert not strat.should_rebalance(make_context(upper, now, lower, upper))


def test_out_of_range_large_range():
    strat = OutOfRangeRebalancer()
    tick = 10**10
    assert strat.should_rebalance(make_context(tick, now, -(10**5), 10**5))


def test_out_of_range_duration_zero_duration(position):
    strat = OutOfRangeDurationRebalancer(duration=timedelta(seconds=0))
    ctx = make_context(950, now, position.tick_lower, position.tick_upper)
    assert strat.should_rebalance(ctx)


def test_out_of_range_never_recovers(position):
    strat = OutOfRangeDurationRebalancer(duration=timedelta(seconds=30))
    lower, upper = position.tick_lower, position.tick_upper
    ts = now

    assert not strat.should_rebalance(make_context(950, ts, lower, upper))
    assert not strat.should_rebalance(
        make_context(950, ts + timedelta(seconds=15), lower, upper)
    )
    assert strat.should_rebalance(
        make_context(950, ts + timedelta(seconds=31), lower, upper)
    )


def test_multi_condition_empty_strategy_list(position):
    strat = MultiConditionRebalancer(strategies=[], mode=LogicMode.OR)
    ctx = make_context(1500, now, position.tick_lower, position.tick_upper)
    assert not strat.should_rebalance(ctx)
