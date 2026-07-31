from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict

from scalper.core.enums import ExecutionBrokerType, ExecutionMode, MarketDataProviderType


class ApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=lambda value: _to_camel(value), populate_by_name=True)


def _to_camel(value: str) -> str:
    first, *rest = value.split("_")
    return first + "".join(word.capitalize() for word in rest)


class HealthResponse(ApiModel):
    status: Literal["ok", "degraded"]
    api_version: str
    execution_mode: ExecutionMode
    market_data_provider: MarketDataProviderType
    execution_broker: ExecutionBrokerType
    timestamp: datetime


class PublicConfigResponse(ApiModel):
    environment: str
    execution_mode: ExecutionMode
    strategy_buying_power_fraction: Decimal
    underlying_quote_stale_seconds: int
    option_quote_stale_seconds: int
    completed_candle_grace_seconds: int
