from fastapi import APIRouter

from scalper.api.v1.schemas import HealthResponse
from scalper.core.config import get_settings
from scalper.core.time import utc_now

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        api_version="1.0.0",
        execution_mode=settings.execution_mode,
        market_data_provider=settings.market_data_provider,
        execution_broker=settings.execution_broker,
        timestamp=utc_now(),
    )
