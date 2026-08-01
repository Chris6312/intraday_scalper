import json

import httpx
import pytest

from scalper.adapters.market_data.public.client import PublicMarketDataClient
from scalper.adapters.market_data.public.errors import (
    PublicConfigurationError,
    PublicResponseError,
)
from scalper.core.config import Settings


def make_settings(*, max_retries: int = 0) -> Settings:
    return Settings(
        _env_file=None,
        public_api_base_url="https://api.public.test",
        public_api_secret="test-secret",
        public_account_id="test-account",
        public_max_retries=max_retries,
    )


@pytest.mark.asyncio
async def test_access_token_is_requested_once_and_cached() -> None:
    request_count = 0
    received_payloads: list[object] = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        received_payloads.append(json.loads(request.content.decode("utf-8")))

        assert request.url.path == ("/userapiauthservice/personal/access-tokens")
        assert "Authorization" not in request.headers

        return httpx.Response(
            200,
            json={"accessToken": "cached-token"},
        )

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(transport=transport) as http_client:
        client = PublicMarketDataClient(
            make_settings(),
            http_client=http_client,
        )

        first = await client.get_access_token()
        second = await client.get_access_token()

    assert first == "cached-token"
    assert second == "cached-token"
    assert request_count == 1
    assert received_payloads == [
        {
            "validityInMinutes": 15,
            "secret": "test-secret",
        }
    ]


@pytest.mark.asyncio
async def test_unauthorized_request_refreshes_token_once() -> None:
    authentication_count = 0
    market_authorizations: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal authentication_count

        if request.url.path.endswith("/personal/access-tokens"):
            authentication_count += 1
            return httpx.Response(
                200,
                json={
                    "accessToken": f"token-{authentication_count}",
                },
            )

        authorization = request.headers["Authorization"]
        market_authorizations.append(authorization)

        if authorization == "Bearer token-1":
            return httpx.Response(401)

        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(transport=transport) as http_client:
        client = PublicMarketDataClient(
            make_settings(),
            http_client=http_client,
        )

        response = await client.request(
            "GET",
            "/userapigateway/marketdata/test-account/test",
        )

    assert response.status_code == 200
    assert authentication_count == 2
    assert market_authorizations == [
        "Bearer token-1",
        "Bearer token-2",
    ]


@pytest.mark.asyncio
async def test_rate_limit_retry_honors_retry_after() -> None:
    authentication_count = 0
    sleep_delays: list[float] = []

    async def record_sleep(delay: float) -> None:
        sleep_delays.append(delay)

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal authentication_count
        authentication_count += 1

        if authentication_count == 1:
            return httpx.Response(
                429,
                headers={"Retry-After": "1.25"},
            )

        return httpx.Response(
            200,
            json={"accessToken": "retried-token"},
        )

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(transport=transport) as http_client:
        client = PublicMarketDataClient(
            make_settings(max_retries=1),
            http_client=http_client,
            sleeper=record_sleep,
        )

        access_token = await client.get_access_token()

    assert access_token == "retried-token"
    assert authentication_count == 2
    assert sleep_delays == [1.25]


@pytest.mark.asyncio
async def test_invalid_authentication_response_is_rejected() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"unexpected": True}))

    async with httpx.AsyncClient(transport=transport) as http_client:
        client = PublicMarketDataClient(
            make_settings(),
            http_client=http_client,
        )

        with pytest.raises(PublicResponseError):
            await client.get_access_token()


def test_missing_public_credentials_are_rejected() -> None:
    with pytest.raises(PublicConfigurationError):
        PublicMarketDataClient(Settings(_env_file=None))
