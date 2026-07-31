from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


class DomainModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    @field_validator("*", mode="before")
    @classmethod
    def reject_naive_datetimes(cls, value: object) -> object:
        if isinstance(value, datetime) and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("all domain datetimes must be timezone-aware")
        return value
