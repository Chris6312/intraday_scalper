from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from scalper.domain.trading import (
    AccountState,
    NewOrder,
    OrderReplacement,
    OrderSnapshot,
    Position,
)


class ExecutionBroker(Protocol):
    async def get_account(self) -> AccountState: ...

    async def submit_order(self, order: NewOrder) -> OrderSnapshot: ...

    async def replace_order(self, replacement: OrderReplacement) -> OrderSnapshot: ...

    async def cancel_order(self, order_id: UUID, idempotency_key: str) -> OrderSnapshot: ...

    async def get_order(self, order_id: UUID) -> OrderSnapshot: ...

    async def list_positions(self) -> Sequence[Position]: ...

    async def flatten_all(self, idempotency_key: str) -> Sequence[OrderSnapshot]: ...
