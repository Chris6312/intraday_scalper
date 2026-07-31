import pytest

from scalper.core.enums import ExecutionMode
from scalper.core.idempotency import deterministic_key
from scalper.services.startup_recovery import RecoveryAction, build_startup_recovery_plan


def test_deterministic_key_is_order_independent() -> None:
    first = deterministic_key("fill", {"order": "A", "qty": 1})
    second = deterministic_key("fill", {"qty": 1, "order": "A"})
    assert first == second


def test_recovery_plan_is_fail_closed_and_complete() -> None:
    plan = build_startup_recovery_plan(ExecutionMode.PAPER)
    assert plan.fail_closed is True
    assert plan.actions[0] is RecoveryAction.ASSERT_PAPER_MODE
    assert plan.actions[-1] is RecoveryAction.EMIT_RECOVERY_REPORT


def test_recovery_rejects_live_mode() -> None:
    with pytest.raises(RuntimeError):
        build_startup_recovery_plan(ExecutionMode.LIVE)
