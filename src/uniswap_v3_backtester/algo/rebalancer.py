from datetime import datetime, timedelta
from enum import Enum
from typing import Annotated, List

from pydantic import BaseModel, Field, field_validator, validate_call


class RebalanceEvent(BaseModel):
    timestamp: datetime
    rebalance_tick: int
    new_tick_lower: int
    new_tick_upper: int


class RebalancerContext(BaseModel):
    tick: int
    timestamp: datetime
    tick_lower: int
    tick_upper: int
    created_at: datetime


class LogicMode(Enum):
    AND = "and"
    OR = "or"


class RebalancingStrategy(BaseModel):
    def should_rebalance(self, context: RebalancerContext) -> bool:
        raise NotImplementedError

    @validate_call
    def rebalance(
        self, context: RebalancerContext, bias: Annotated[float, Field(ge=0.0, le=1.0)]
    ) -> tuple[int, int]:
        raise NotImplementedError

    def get_event_at(self, timestamp: datetime) -> RebalanceEvent | None:
        raise NotImplementedError


# --- Strategy Implementations ---


class TimeTriggeredRebalancer(RebalancingStrategy):
    interval: timedelta
    last_rebalanced_at: datetime | None = None
    _events: list[RebalanceEvent] = []

    @field_validator("interval")
    @classmethod
    def validate_interval(cls, v: timedelta) -> timedelta:
        if v.total_seconds() < 0:
            raise ValueError("Interval must be non-negative")
        return v

    def should_rebalance(self, context: RebalancerContext) -> bool:
        check_tick_upper_greater_than_lower(context.tick_lower, context.tick_upper)
        reference = self.last_rebalanced_at or context.created_at
        return (context.timestamp - reference) > self.interval

    def rebalance(self, context: RebalancerContext, bias: float) -> tuple[int, int]:
        width = context.tick_upper - context.tick_lower
        new_lower, new_upper = compute_tick_range(context.tick, width, bias)
        self.last_rebalanced_at = context.timestamp
        self._events.append(
            RebalanceEvent(
                timestamp=context.timestamp,
                rebalance_tick=context.tick,
                new_tick_lower=new_lower,
                new_tick_upper=new_upper,
            )
        )
        return new_lower, new_upper

    def get_event_at(self, timestamp: datetime) -> RebalanceEvent | None:
        return next((e for e in self._events if e.timestamp == timestamp), None)


class OutOfRangeRebalancer(RebalancingStrategy):
    _events: list[RebalanceEvent] = []

    def should_rebalance(self, context: RebalancerContext) -> bool:
        check_tick_upper_greater_than_lower(context.tick_lower, context.tick_upper)
        return not (context.tick_lower <= context.tick <= context.tick_upper)

    def rebalance(self, context: RebalancerContext, bias: float) -> tuple[int, int]:
        width = context.tick_upper - context.tick_lower
        new_lower, new_upper = compute_tick_range(context.tick, width, bias)
        self._events.append(
            RebalanceEvent(
                timestamp=context.timestamp,
                rebalance_tick=context.tick,
                new_tick_lower=new_lower,
                new_tick_upper=new_upper,
            )
        )
        return new_lower, new_upper

    def get_event_at(self, timestamp: datetime) -> RebalanceEvent | None:
        return next((e for e in self._events if e.timestamp == timestamp), None)


class OutOfRangeDurationRebalancer(RebalancingStrategy):
    duration: timedelta
    out_of_range_since: datetime | None = None
    _events: list[RebalanceEvent] = []

    def should_rebalance(self, context: RebalancerContext) -> bool:
        check_tick_upper_greater_than_lower(context.tick_lower, context.tick_upper)
        in_range = context.tick_lower <= context.tick <= context.tick_upper

        if in_range:
            self.out_of_range_since = None
            return False

        reference = self.out_of_range_since or context.created_at
        return (context.timestamp - reference) >= self.duration

    def rebalance(self, context: RebalancerContext, bias: float) -> tuple[int, int]:
        width = context.tick_upper - context.tick_lower
        new_lower, new_upper = compute_tick_range(context.tick, width, bias)
        self.out_of_range_since = None
        self._events.append(
            RebalanceEvent(
                timestamp=context.timestamp,
                rebalance_tick=context.tick,
                new_tick_lower=new_lower,
                new_tick_upper=new_upper,
            )
        )
        return new_lower, new_upper

    def get_event_at(self, timestamp: datetime) -> RebalanceEvent | None:
        return next((e for e in self._events if e.timestamp == timestamp), None)


class MultiConditionRebalancer(RebalancingStrategy):
    strategies: List[RebalancingStrategy]
    mode: LogicMode

    def should_rebalance(self, context: RebalancerContext) -> bool:
        check_tick_upper_greater_than_lower(context.tick_lower, context.tick_upper)
        if not self.strategies:
            return False
        checks = [s.should_rebalance(context) for s in self.strategies]
        return all(checks) if self.mode == LogicMode.AND else any(checks)

    def rebalance(self, context: RebalancerContext, bias: float) -> tuple[int, int]:
        for s in self.strategies:
            if s.should_rebalance(context):
                return s.rebalance(context, bias)
        raise RuntimeError("No eligible strategy triggered rebalance.")

    def get_event_at(self, timestamp: datetime) -> RebalanceEvent | None:
        for s in self.strategies:
            event = s.get_event_at(timestamp)
            if event:
                return event
        return None


def compute_tick_range(tick: int, width: int, bias: float) -> tuple[int, int]:
    """
    Compute new tick_lower and tick_upper from center tick, width, and bias.
    - bias = 0.5 → balanced around tick
    - bias = 0.0 → all above tick (token0-heavy)
    - bias = 1.0 → all below tick (token1-heavy)
    """
    if not 0.0 <= bias <= 1.0:
        raise ValueError("Bias must be between 0.0 and 1.0")

    left = int(width * bias)
    right = width - left
    return tick - left, tick + right


def check_tick_upper_greater_than_lower(tick_lower: int, tick_upper: int) -> None:
    if tick_upper < tick_lower:
        raise ValueError("tick_upper must be >= tick_lower")
