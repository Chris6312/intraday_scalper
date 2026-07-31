from datetime import UTC, datetime
from zoneinfo import ZoneInfo

EASTERN = ZoneInfo("America/New_York")


def utc_now() -> datetime:
    return datetime.now(UTC)


def require_aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime must be timezone-aware")
    return value


def to_utc(value: datetime) -> datetime:
    return require_aware(value).astimezone(UTC)


def to_eastern(value: datetime) -> datetime:
    return require_aware(value).astimezone(EASTERN)
