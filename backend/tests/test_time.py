from datetime import UTC, datetime, timedelta

from scalper.core.time import to_eastern


def test_eastern_timezone_observes_daylight_saving_time() -> None:
    summer = to_eastern(datetime(2026, 7, 30, 16, 0, tzinfo=UTC))
    winter = to_eastern(datetime(2026, 1, 30, 16, 0, tzinfo=UTC))

    assert summer.utcoffset() == timedelta(hours=-4)
    assert winter.utcoffset() == timedelta(hours=-5)
