from fastapi import APIRouter

from scalper.api.v1.schemas import PublicConfigResponse
from scalper.core.config import get_settings

router = APIRouter(tags=["system"])


@router.get("/meta/config", response_model=PublicConfigResponse)
async def public_config() -> PublicConfigResponse:
    settings = get_settings()
    return PublicConfigResponse(
        environment=settings.app_env,
        execution_mode=settings.execution_mode,
        strategy_buying_power_fraction=settings.strategy_buying_power_fraction,
        underlying_quote_stale_seconds=settings.underlying_quote_stale_seconds,
        option_quote_stale_seconds=settings.option_quote_stale_seconds,
        completed_candle_grace_seconds=settings.completed_candle_grace_seconds,
    )
