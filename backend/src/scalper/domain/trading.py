from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field, model_validator

from scalper.core.enums import (
    CashEventType,
    ExecutionBrokerType,
    OptionRight,
    OrderSide,
    OrderState,
    OrderType,
    PositionState,
    TimeInForce,
)
from scalper.domain.base import DomainModel


class NewOrder(DomainModel):
    order_id: UUID
    ledger_session_id: UUID
    idempotency_key: str
    underlying: str
    option_symbol: str
    right: OptionRight
    side: OrderSide
    quantity: int = Field(gt=0, le=5)
    order_type: OrderType = OrderType.LIMIT
    time_in_force: TimeInForce = TimeInForce.DAY
    limit_price: Decimal = Field(gt=0)
    maximum_permitted_price: Decimal = Field(gt=0)
    submitted_at: datetime

    @model_validator(mode="after")
    def validate_buy_price_cap(self) -> "NewOrder":
        if self.side is OrderSide.BUY and self.limit_price > self.maximum_permitted_price:
            raise ValueError("buy limit exceeds maximum permitted price")
        return self


class OrderReplacement(DomainModel):
    order_id: UUID
    idempotency_key: str
    prior_limit_price: Decimal = Field(gt=0)
    new_limit_price: Decimal = Field(gt=0)
    maximum_permitted_price: Decimal = Field(gt=0)
    requested_at: datetime

    @model_validator(mode="after")
    def enforce_cap(self) -> "OrderReplacement":
        if self.new_limit_price > self.maximum_permitted_price:
            raise ValueError("replacement exceeds maximum permitted price")
        return self


class OrderSnapshot(DomainModel):
    order_id: UUID
    ledger_session_id: UUID
    state: OrderState
    total_quantity: int = Field(gt=0, le=5)
    filled_quantity: int = Field(ge=0, le=5)
    limit_price: Decimal = Field(gt=0)
    average_fill_price: Decimal | None = Field(default=None, gt=0)
    updated_at: datetime

    @model_validator(mode="after")
    def validate_filled_quantity(self) -> "OrderSnapshot":
        if self.filled_quantity > self.total_quantity:
            raise ValueError("filled quantity cannot exceed total quantity")
        return self


class Fill(DomainModel):
    fill_id: UUID
    external_fill_id: str
    execution_broker: ExecutionBrokerType
    ledger_session_id: UUID
    order_id: UUID
    option_symbol: str
    side: OrderSide
    quantity: int = Field(gt=0, le=5)
    price: Decimal = Field(gt=0)
    fee: Decimal = Field(ge=0)
    filled_at: datetime
    quote_sequence: str | None = None


class Position(DomainModel):
    position_id: UUID
    ledger_session_id: UUID
    underlying: str
    option_symbol: str
    right: OptionRight
    state: PositionState
    initial_quantity: int = Field(gt=0, le=5)
    open_quantity: int = Field(ge=0, le=5)
    average_entry_price: Decimal = Field(gt=0)
    opened_at: datetime
    first_fill_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def validate_open_quantity(self) -> "Position":
        if self.open_quantity > self.initial_quantity:
            raise ValueError("open quantity cannot exceed initial quantity")
        return self


class AccountState(DomainModel):
    ledger_session_id: UUID
    cash: Decimal
    buying_power: Decimal
    reserved_capital: Decimal = Field(ge=0)
    open_position_cost: Decimal = Field(ge=0)
    net_account_value: Decimal
    realized_pnl: Decimal
    unrealized_liquidation_pnl: Decimal
    fees: Decimal = Field(ge=0)
    as_of: datetime


class CashEvent(DomainModel):
    cash_event_id: UUID
    ledger_session_id: UUID
    idempotency_key: str
    event_type: CashEventType
    amount: Decimal
    occurred_at: datetime
    related_order_id: UUID | None = None
    related_fill_id: UUID | None = None
