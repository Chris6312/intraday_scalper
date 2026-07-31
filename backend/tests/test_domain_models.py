from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from scalper.domain.market import Bar, Quote


def test_quote_midpoint_uses_decimal() -> None:
    now = datetime.now(UTC)
    quote = Quote(
        symbol="NVDA260729C00200000",
        bid=Decimal("1.00"),
        ask=Decimal("1.10"),
        source_timestamp=now,
        received_timestamp=now,
    )
    assert quote.midpoint == Decimal("1.05")


def test_naive_datetime_is_rejected() -> None:
    now = datetime.now()
    with pytest.raises(ValidationError):
        Quote(
            symbol="SPY",
            bid=Decimal("1.00"),
            ask=Decimal("1.01"),
            source_timestamp=now,
            received_timestamp=now,
        )


def test_inconsistent_bar_is_rejected() -> None:
    now = datetime.now(UTC)
    with pytest.raises(ValidationError):
        Bar(
            symbol="SPY",
            timeframe="5m",
            open_time=now,
            close_time=now + timedelta(minutes=5),
            open=Decimal("100"),
            high=Decimal("99"),
            low=Decimal("98"),
            close=Decimal("99"),
            volume=100,
            is_complete=True,
        )
