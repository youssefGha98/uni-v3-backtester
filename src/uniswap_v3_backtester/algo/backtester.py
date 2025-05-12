from datetime import datetime
from decimal import Decimal
from typing import List, Tuple
from pydantic import BaseModel, ConfigDict

from uniswap_v3_backtester.algo.math import compute_token1_for_fixed_token0
from uniswap_v3_backtester.algo.pool import Position, Swap, SwapSeries
from uniswap_v3_backtester.algo.activity import ActivityTracker, ActivityTimeseries
from uniswap_v3_backtester.algo.fees import FeeCalculator, FeeTimeseries
from uniswap_v3_backtester.algo.Impermanent_Loss import ImpermanentLossTracker, ILTimeseries
from uniswap_v3_backtester.algo.apr import APRTracker, APRTimeseries
from uniswap_v3_backtester.algo.rebalancer import RebalanceEvent, RebalancerContext, RebalancingStrategy


class PositionSimulationContext(BaseModel):
    position: Position
    created_at: datetime
    swap_series: SwapSeries
    tracker: ActivityTracker
    calculator: FeeCalculator
    il_tracker: ImpermanentLossTracker | None = None
    apr_tracker: APRTracker | None = None
    rebalancer: RebalancingStrategy | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


class BacktestResult(BaseModel):
    total_fees_token0: Decimal
    total_fees_token1: Decimal
    apr_series: APRTimeseries
    activity_series: ActivityTimeseries
    fee_series: FeeTimeseries
    il_series: ILTimeseries
    realized_il: ILTimeseries
    token_balance_series: List[Tuple[datetime, Decimal, Decimal]]
    token_composition_series: List[Tuple[datetime, Decimal, Decimal]]
    swap_ticks: List[Tuple[datetime, int]]
    initial_tick_lower: int
    initial_tick_upper: int
    rebalancing_events: List[RebalanceEvent]

    @classmethod
    def from_simulation(
        cls,
        context: PositionSimulationContext,
        apr_series: APRTimeseries,
        token_balances: List[Tuple[datetime, Decimal, Decimal]],
        token_composition: List[Tuple[datetime, Decimal, Decimal]],
        rebalancing_events: List[RebalanceEvent]
    ):
        return cls(
            total_fees_token0=context.calculator.get_total_fees().token0,
            total_fees_token1=context.calculator.get_total_fees().token1,
            apr_series=apr_series,
            activity_series=context.tracker.get_timeseries(),
            fee_series=context.calculator.get_timeseries(),
            il_series=context.il_tracker.get_il_series() if context.il_tracker else ILTimeseries(timestamps=[], values=[]),
            realized_il=context.il_tracker.get_realized_il_series() if context.il_tracker else ILTimeseries(timestamps=[], values=[]),
            token_balance_series=token_balances,
            token_composition_series=token_composition,
            swap_ticks=[(swap.timestamp, swap.tick) for swap in context.swap_series.swaps],
            initial_tick_lower=context.position.tick_lower,
            initial_tick_upper=context.position.tick_upper,
            rebalancing_events=rebalancing_events
        )


class BacktestOutput(BaseModel):
    results: List[BacktestResult]

class GlobalClockBacktestRunner:
    def __init__(self, contexts: List[PositionSimulationContext]):
        self.contexts = contexts
        self.global_timestamps = sorted(
            {swap.timestamp for ctx in contexts for swap in ctx.swap_series.swaps}
        )
        self.token_balances = [[] for _ in contexts]
        self.token_compositions = [[] for _ in contexts]
        self.tick_contexts = [{} for _ in contexts]
        self.rebalance_events = [[] for _ in contexts]

    def run(self) -> BacktestOutput:
        for t in self.global_timestamps:
            for i, context in enumerate(self.contexts):
                swaps_at_t = [s for s in context.swap_series.swaps if s.timestamp == t]
                for swap in swaps_at_t:
                    self._process_swap(i, context, swap, t)
        return self._finalize_results()

    def _process_swap(self, i: int, context: PositionSimulationContext, swap: Swap, timestamp: datetime):
        position = context.position
        tracker = context.tracker
        calculator = context.calculator
        il_tracker = context.il_tracker
        apr_tracker = context.apr_tracker

        self.token_compositions[i].append((timestamp, position.amount0, position.amount1))

        tracker.track(swap)

        rebalancer = context.rebalancer

        if rebalancer:
            rebalance_context = RebalancerContext(
                tick=swap.tick,
                timestamp=timestamp,
                tick_lower=position.tick_lower,
                tick_upper=position.tick_upper,
                created_at=context.created_at
            )

            if rebalancer.should_rebalance(rebalance_context):
                new_lower, new_upper = rebalancer.rebalance(rebalance_context, bias=0.5)
                width = new_upper - new_lower

                # Recompute position
                L, new_amount1 = compute_token1_for_fixed_token0(position.amount0, new_lower, new_upper, swap.tick)

                # Replace the position
                position.tick_lower = new_lower
                position.tick_upper = new_upper
                position.amount1 = new_amount1
                rebalance_event = rebalancer.get_event_at(timestamp)
                if rebalance_event:
                    self.rebalance_events[i].append(rebalance_event)

        is_active = tracker.is_active(swap.tick)
        calculator.track(swap, is_active)
        if il_tracker:
            il_tracker.track_il(timestamp, swap.tick)

        self.tick_contexts[i][timestamp] = swap.tick

        if apr_tracker:
            latest_fee = calculator._fees[-1]
            apr_tracker.track(
                timestamp=swap.timestamp,
                token0=position.amount0,
                token1=position.amount1,
                fee_token0=calculator.get_total_fees().token0,
                fee_token1=calculator.get_total_fees().token1,
                sqrtPriceX96=swap.sqrt_price_x96
            )

        self.token_balances[i].append((timestamp, position.amount0, position.amount1))

    def _finalize_results(self) -> BacktestOutput:
        results = []

        for i, context in enumerate(self.contexts):
            apr_tracker = context.apr_tracker

            if apr_tracker:
                daily_dates = sorted({datetime(ts.year, ts.month, ts.day) for ts in self.global_timestamps})
                apr_series = apr_tracker.compute_apr_on_dates(daily_dates)
            else:
                apr_series = APRTimeseries(dates=[], aprs=[])

            results.append(
                BacktestResult.from_simulation(
                    context=context,
                    apr_series=apr_series,
                    token_balances=self.token_balances[i],
                    token_composition=self.token_compositions[i],
                    rebalancing_events=self.rebalance_events[i]
                )
            )

        return BacktestOutput(results=results)
