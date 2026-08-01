from datetime import datetime
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
