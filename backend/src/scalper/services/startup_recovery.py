from dataclasses import dataclass
from enum import StrEnum

from scalper.core.enums import ExecutionMode


class RecoveryAction(StrEnum):
    ASSERT_PAPER_MODE = "ASSERT_PAPER_MODE"
    ACQUIRE_LEDGER_LOCK = "ACQUIRE_LEDGER_LOCK"
    REPLAY_IMMUTABLE_EVENTS = "REPLAY_IMMUTABLE_EVENTS"
    VERIFY_SNAPSHOTS = "VERIFY_SNAPSHOTS"
    MARK_QUOTES_STALE = "MARK_QUOTES_STALE"
    RESTORE_POSITION_MANAGEMENT = "RESTORE_POSITION_MANAGEMENT"
    CANCEL_ORPHANED_ENTRIES = "CANCEL_ORPHANED_ENTRIES"
    RESTORE_CIRCUIT_BREAKERS = "RESTORE_CIRCUIT_BREAKERS"
    EMIT_RECOVERY_REPORT = "EMIT_RECOVERY_REPORT"


@dataclass(frozen=True, slots=True)
class RecoveryPlan:
    actions: tuple[RecoveryAction, ...]
    fail_closed: bool = True


def build_startup_recovery_plan(execution_mode: ExecutionMode) -> RecoveryPlan:
    if execution_mode is not ExecutionMode.PAPER:
        raise RuntimeError("Version 1 recovery is available only in PAPER mode")
    return RecoveryPlan(actions=tuple(RecoveryAction))
