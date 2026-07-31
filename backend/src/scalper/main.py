from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from scalper.api.v1.router import router as api_v1_router
from scalper.core.config import get_settings
from scalper.core.logging import configure_logging, log_event


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    settings.assert_version_one_safety()
    configure_logging(settings.log_level)
    log_event(
        "application_started",
        environment=settings.app_env,
        execution_mode=settings.execution_mode.value,
    )
    yield
    log_event("application_stopped")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Options Intraday Scalper API",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.web_origin],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )
    app.include_router(api_v1_router, prefix="/api/v1")
    return app


app = create_app()
