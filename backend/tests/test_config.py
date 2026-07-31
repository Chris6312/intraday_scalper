from decimal import Decimal

import pytest
from pydantic import ValidationError

from scalper.core.config import Settings
from scalper.core.enums import ExecutionBrokerType, ExecutionMode


def test_defaults_enforce_approved_strategy_ceiling() -> None:
    settings = Settings(_env_file=None)
    assert settings.paper_starting_balance == Decimal("25000.00")
    assert settings.strategy_buying_power_fraction == Decimal("0.50")
    settings.assert_version_one_safety()


def test_fraction_cannot_exceed_fifty_percent() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, strategy_buying_power_fraction=Decimal("0.51"))


def test_version_one_rejects_live_or_external_broker() -> None:
    with pytest.raises(RuntimeError):
        Settings(_env_file=None, execution_mode=ExecutionMode.LIVE).assert_version_one_safety()
    with pytest.raises(RuntimeError):
        Settings(
            _env_file=None,
            execution_broker=ExecutionBrokerType.WEBULL,
        ).assert_version_one_safety()
