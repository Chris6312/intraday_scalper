from datetime import date, datetime
from decimal import Decimal

from pydantic import Field, model_validator

from scalper.core.enums import OptionRight
from scalper.domain.base import DomainModel


class Bar(DomainModel):
    symbol: str
    timeframe: str
    open_time: datetime
    close_time: datetime
    open: Decimal = Field(ge=0)
    high: Decimal = Field(ge=0)
    low: Decimal = Field(ge=0)
    close: Decimal = Field(ge=0)
    volume: int = Field(ge=0)
    is_complete: bool

    @model_validator(mode="after")
    def validate_bar(self) -> "Bar":
        if self.close_time <= self.open_time:
            raise ValueError("bar close_time must be after open_time")
        if self.high < max(self.open, self.close, self.low):
            raise ValueError("bar high is inconsistent")
        if self.low > min(self.open, self.close, self.high):
            raise ValueError("bar low is inconsistent")
        return self


class Quote(DomainModel):
    symbol: str
    bid: Decimal = Field(ge=0)
    ask: Decimal = Field(ge=0)
    bid_size: int | None = Field(default=None, ge=0)
    ask_size: int | None = Field(default=None, ge=0)
    source_timestamp: datetime
    received_timestamp: datetime
    sequence: str | None = None

    @model_validator(mode="after")
    def validate_market(self) -> "Quote":
        if self.ask and self.bid > self.ask:
            raise ValueError("crossed quote is not a valid canonical quote")
        return self

    @property
    def midpoint(self) -> Decimal:
        return (self.bid + self.ask) / Decimal("2")


class OptionExpiration(DomainModel):
    underlying: str
    expiration: date
    dte: int = Field(ge=0)


class OptionGreeks(DomainModel):
    delta: Decimal | None = None
    gamma: Decimal | None = None
    theta: Decimal | None = None
    vega: Decimal | None = None
    rho: Decimal | None = None
    implied_volatility: Decimal | None = Field(default=None, ge=0)


class OptionContract(DomainModel):
    symbol: str
    underlying: str
    expiration: date
    strike: Decimal = Field(gt=0)
    right: OptionRight
    quote: Quote
    volume: int | None = Field(default=None, ge=0)
    open_interest: int | None = Field(default=None, ge=0)
    greeks: OptionGreeks | None = None
    tick_size: Decimal = Field(gt=0)


class OptionChain(DomainModel):
    underlying: str
    expiration: date
    calls: tuple[OptionContract, ...]
    puts: tuple[OptionContract, ...]
    source_timestamp: datetime
    received_timestamp: datetime
