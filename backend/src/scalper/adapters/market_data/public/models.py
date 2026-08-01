from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PublicModel(BaseModel):
    model_config = ConfigDict(
        extra="ignore",
        populate_by_name=True,
        str_strip_whitespace=True,
        allow_inf_nan=False,
    )


class PublicAccessTokenResponse(PublicModel):
    access_token: str = Field(alias="accessToken", min_length=1)


class PublicQuoteInstrument(PublicModel):
    symbol: str = Field(min_length=1)
    instrument_type: Literal["EQUITY"] = Field(alias="type")


class PublicQuotePayload(PublicModel):
    instrument: PublicQuoteInstrument
    outcome: str = Field(min_length=1)
    bid: Decimal = Field(ge=0)
    ask: Decimal = Field(ge=0)
    bid_size: int | None = Field(default=None, alias="bidSize", ge=0)
    ask_size: int | None = Field(default=None, alias="askSize", ge=0)
    bid_timestamp: datetime = Field(alias="bidTimestamp")
    ask_timestamp: datetime = Field(alias="askTimestamp")

    @field_validator("bid_timestamp", "ask_timestamp")
    @classmethod
    def require_aware_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Public quote timestamps must be timezone-aware")
        return value


class PublicQuotesResponse(PublicModel):
    quotes: list[PublicQuotePayload]


class PublicOptionExpirationsResponse(PublicModel):
    base_symbol: str = Field(alias="baseSymbol", min_length=1)
    expirations: list[date]


class PublicOptionInstrument(PublicModel):
    symbol: str = Field(min_length=1)
    instrument_type: Literal["OPTION"] = Field(alias="type")


class PublicOptionGreeksPayload(PublicModel):
    delta: Decimal | None = None
    gamma: Decimal | None = None
    theta: Decimal | None = None
    vega: Decimal | None = None
    rho: Decimal | None = None
    implied_volatility: Decimal | None = Field(
        default=None,
        alias="impliedVolatility",
        ge=0,
    )


class PublicOptionDetailsPayload(PublicModel):
    greeks: PublicOptionGreeksPayload | None = None
    strike_price: Decimal = Field(alias="strikePrice", gt=0)


class PublicOptionChainContractPayload(PublicModel):
    instrument: PublicOptionInstrument
    outcome: str = Field(min_length=1)
    bid: Decimal = Field(ge=0)
    ask: Decimal = Field(ge=0)
    bid_size: int | None = Field(default=None, alias="bidSize", ge=0)
    ask_size: int | None = Field(default=None, alias="askSize", ge=0)
    bid_timestamp: datetime = Field(alias="bidTimestamp")
    ask_timestamp: datetime = Field(alias="askTimestamp")
    volume: int | None = Field(default=None, ge=0)
    open_interest: int | None = Field(default=None, alias="openInterest", ge=0)
    option_details: PublicOptionDetailsPayload = Field(alias="optionDetails")

    @field_validator("bid_timestamp", "ask_timestamp")
    @classmethod
    def require_aware_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Public option timestamps must be timezone-aware")
        return value


class PublicOptionChainResponse(PublicModel):
    base_symbol: str = Field(alias="baseSymbol", min_length=1)
    calls: list[PublicOptionChainContractPayload]
    puts: list[PublicOptionChainContractPayload]


class PublicBarPayload(PublicModel):
    timestamp: datetime
    open: Decimal = Field(ge=0)
    close: Decimal = Field(ge=0)
    high: Decimal = Field(ge=0)
    low: Decimal = Field(ge=0)
    volume: int = Field(ge=0)

    @field_validator("timestamp")
    @classmethod
    def require_aware_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Public bar timestamps must be timezone-aware")
        return value


class PublicBarSeries(PublicModel):
    bars: list[PublicBarPayload]


class PublicBarsResponse(PublicModel):
    symbol: str = Field(min_length=1)
    period: Literal["DAY"]
    regular_market: PublicBarSeries = Field(alias="regularMarket")
