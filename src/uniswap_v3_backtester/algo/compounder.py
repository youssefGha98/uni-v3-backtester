from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import List

from pydantic import BaseModel, Field, field_validator

from uniswap_v3_backtester.algo.fees import Fee
from uniswap_v3_backtester.algo.pool import Position


class LogicMode(Enum):
    AND = "and"
    OR = "or"


class CompoundEvent(BaseModel):
    timestamp: datetime
    added_token0: Decimal
    added_token1: Decimal


class CompounderContext(BaseModel):
    timestamp: datetime
    created_at: datetime
    accumulated_fees: Fee


class CompounderTrigger(BaseModel):
    def is_triggered(self, context: CompounderContext) -> bool:
        raise NotImplementedError


class TimeTrigger(CompounderTrigger):
    start_delay: timedelta
    last_compounded: datetime | None = None

    @field_validator("start_delay")
    @classmethod
    def validate_delay(cls, v: timedelta) -> timedelta:
        if v.total_seconds() < 0:
            raise ValueError("start_delay must be non-negative")
        return v

    def is_triggered(self, context: CompounderContext) -> bool:
        reference_time = self.last_compounded or context.created_at
        return (context.timestamp - reference_time) >= self.start_delay



class Compounder(BaseModel):
    interval: timedelta = Field(..., description="Minimum duration between compounds")
    triggers: List[CompounderTrigger] = []
    mode: LogicMode = LogicMode.OR
    last_compounded: datetime | None = None

    _compound_events: List[CompoundEvent] = []

    @field_validator("interval")
    @classmethod
    def validate_interval(cls, v: timedelta) -> timedelta:
        if v.total_seconds() < 0:
            raise ValueError("interval must be non-negative")
        return v

    def should_compound(self, context: CompounderContext) -> bool:
        if (
            self.last_compounded
            and (context.timestamp - self.last_compounded) < self.interval
        ):
            return False

        if not self.triggers:
            return True

        results = [t.is_triggered(context) for t in self.triggers]
        return all(results) if self.mode == LogicMode.AND else any(results)

    def compound(
        self, position: Position, fees: Fee, context: CompounderContext
    ) -> None:
        position.amount0 += fees.token0
        position.amount1 += fees.token1
        self._compound_events.append(
            CompoundEvent(
                timestamp=context.timestamp,
                added_token0=fees.token0,
                added_token1=fees.token1,
            )
        )
        context.accumulated_fees = Fee(token0=Decimal(0), token1=Decimal(0))
        self.last_compounded = context.timestamp

    def get_event_at(self, timestamp: datetime) -> CompoundEvent | None:
        for event in self._compound_events:
            if event.timestamp == timestamp:
                return event
        return None

    def get_total_compounded_fees(self) -> Fee:
        total_token0 = sum(
            (e.added_token0 for e in self._compound_events), start=Decimal("0")
        )
        total_token1 = sum(
            (e.added_token1 for e in self._compound_events), start=Decimal("0")
        )
        return Fee(token0=total_token0, token1=total_token1)
