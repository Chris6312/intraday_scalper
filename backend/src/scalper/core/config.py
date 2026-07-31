from decimal import Decimal
from functools import lru_cache

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from scalper.core.enums import ExecutionBrokerType, ExecutionMode, MarketDataProviderType


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: str = "local"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    web_origin: str = "http://localhost:5173"

    execution_mode: ExecutionMode = ExecutionMode.PAPER
    market_data_provider: MarketDataProviderType = MarketDataProviderType.PUBLIC
    execution_broker: ExecutionBrokerType = ExecutionBrokerType.INTERNAL_PAPER

    database_url: str = "postgresql+asyncpg://scalper:scalper@localhost:5432/options_scalper"

    public_api_base_url: str = "https://api.public.com"
    public_api_secret: SecretStr | None = None
    public_account_id: SecretStr | None = None
    public_access_token_ttl_minutes: int = 15

    paper_starting_balance: Decimal = Decimal("25000.00")
    strategy_buying_power_fraction: Decimal = Decimal("0.50")

    sim_commission_per_contract_per_side: Decimal = Decimal("0.65")
    sim_regulatory_fee_per_sell_contract: Decimal = Decimal("0.03")
    sim_entry_slippage_ticks: int = 1
    sim_normal_exit_slippage_ticks: int = 1
    sim_stop_slippage_ticks: int = 2
    sim_unknown_size_max_contracts_per_quote: int = 1
    sim_unknown_size_refill_delay_ms: int = 250

    underlying_quote_stale_seconds: int = 5
    option_quote_stale_seconds: int = 3
    completed_candle_grace_seconds: int = 2

    alpaca_comparison_enabled: bool = False
    webull_adapter_enabled: bool = False

    @field_validator(
        "paper_starting_balance",
        "sim_commission_per_contract_per_side",
        "sim_regulatory_fee_per_sell_contract",
    )
    @classmethod
    def require_nonnegative_money(cls, value: Decimal) -> Decimal:
        if value < 0:
            raise ValueError("money configuration cannot be negative")
        return value

    @field_validator("strategy_buying_power_fraction")
    @classmethod
    def validate_strategy_fraction(cls, value: Decimal) -> Decimal:
        if value <= 0 or value > Decimal("0.50"):
            raise ValueError("strategy buying-power fraction must be greater than 0 and at most 0.50")
        return value

    @field_validator(
        "sim_entry_slippage_ticks",
        "sim_normal_exit_slippage_ticks",
        "sim_stop_slippage_ticks",
        "sim_unknown_size_max_contracts_per_quote",
        "sim_unknown_size_refill_delay_ms",
        "underlying_quote_stale_seconds",
        "option_quote_stale_seconds",
        "completed_candle_grace_seconds",
    )
    @classmethod
    def require_nonnegative_integer(cls, value: int, info: object) -> int:
        if value < 0:
            raise ValueError("integer configuration cannot be negative")
        return value

    def assert_version_one_safety(self) -> None:
        if self.execution_mode is not ExecutionMode.PAPER:
            raise RuntimeError("Version 1 refuses to start outside PAPER mode")
        if self.execution_broker is not ExecutionBrokerType.INTERNAL_PAPER:
            raise RuntimeError("Version 1 requires INTERNAL_PAPER execution")
        if self.webull_adapter_enabled:
            raise RuntimeError("Webull adapter cannot be enabled in Version 1")

    def has_public_credentials(self) -> bool:
        return bool(self.public_api_secret and self.public_account_id)


@lru_cache
def get_settings() -> Settings:
    return Settings()
