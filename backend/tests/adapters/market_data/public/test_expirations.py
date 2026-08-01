import json
from datetime import UTC, datetime

import httpx
import pytest

from scalper.adapters.market_data.public.client import PublicMarketDataClient
from scalper.adapters.market_data.public.errors import PublicHttpError, PublicResponseError
from scalper.core.config import Settings


def make_settings(*, account_id: str = "test-account") -> Settings:
    return Settings(
        _env_file=None,
        public_api_base_url="https://api.public.test",
        public_api_secret="test-secret",
        public_account_id=account_id,
        public_max_retries=0,
    )


def make_payload(
    *,
    base_symbol: str = "AAPL",
    expirations: object = None,
) -> dict[str, object]:
    if expirations is None:
        expirations = ["2026-08-07", "2026-07-31", "2026-08-05"]
    return {
        "baseSymbol": base_symbol,
        "expirations": expirations,
    }


def expiration_transport(payload: object) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/personal/access-tokens"):
            return httpx.Response(200, json={"accessToken": "token"})
        return httpx.Response(200, json=payload)

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_get_option_expirations_maps_sorts_and_calculates_eastern_dte() -> None:
    received_at = datetime(2026, 7, 31, 16, 0, tzinfo=UTC)
    market_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/personal/access-tokens"):
            return httpx.Response(200, json={"accessToken": "expiration-token"})
        market_requests.append(request)
        return httpx.Response(200, json=make_payload())

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = PublicMarketDataClient(
            make_settings(),
            http_client=http_client,
            clock=lambda: received_at,
        )
        expirations = await client.get_option_expirations("aapl")

    request = market_requests[0]
    assert request.method == "POST"
    assert request.url.path == ("/userapigateway/marketdata/test-account/option-expirations")
    assert request.headers["Authorization"] == "Bearer expiration-token"
    assert json.loads(request.content.decode("utf-8")) == {
        "instrument": {"symbol": "AAPL", "type": "EQUITY"}
    }

    assert [(item.expiration.isoformat(), item.dte) for item in expirations] == [
        ("2026-07-31", 0),
        ("2026-08-05", 5),
        ("2026-08-07", 7),
    ]
    assert all(item.underlying == "AAPL" for item in expirations)


@pytest.mark.asyncio
async def test_get_option_expirations_uses_eastern_calendar_date() -> None:
    # 02:00 UTC on August 1 is still July 31 in New York.
    clock_value = datetime(2026, 8, 1, 2, 0, tzinfo=UTC)
    payload = make_payload(expirations=["2026-07-31", "2026-08-03"])

    async with httpx.AsyncClient(transport=expiration_transport(payload)) as http_client:
        expirations = await PublicMarketDataClient(
            make_settings(),
            http_client=http_client,
            clock=lambda: clock_value,
        ).get_option_expirations("AAPL")

    assert [item.dte for item in expirations] == [0, 3]


@pytest.mark.asyncio
async def test_get_option_expirations_returns_empty_when_public_lists_none() -> None:
    async with httpx.AsyncClient(
        transport=expiration_transport(make_payload(expirations=[]))
    ) as http_client:
        expirations = await PublicMarketDataClient(
            make_settings(),
            http_client=http_client,
        ).get_option_expirations("AAPL")

    assert expirations == ()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {"expirations": ["2026-08-07"]},
        {"baseSymbol": "AAPL"},
        {"baseSymbol": "AAPL", "expirations": ["not-a-date"]},
        {"baseSymbol": "AAPL", "expirations": "2026-08-07"},
    ],
)
async def test_get_option_expirations_rejects_malformed_payload(payload: object) -> None:
    async with httpx.AsyncClient(transport=expiration_transport(payload)) as http_client:
        client = PublicMarketDataClient(make_settings(), http_client=http_client)
        with pytest.raises(PublicResponseError, match="response was invalid"):
            await client.get_option_expirations("AAPL")


@pytest.mark.asyncio
async def test_get_option_expirations_rejects_wrong_base_symbol() -> None:
    payload = make_payload(base_symbol="MSFT")
    async with httpx.AsyncClient(transport=expiration_transport(payload)) as http_client:
        client = PublicMarketDataClient(make_settings(), http_client=http_client)
        with pytest.raises(PublicResponseError, match="symbol did not match"):
            await client.get_option_expirations("AAPL")


@pytest.mark.asyncio
async def test_get_option_expirations_rejects_duplicate_dates() -> None:
    payload = make_payload(expirations=["2026-08-07", "2026-08-07"])
    async with httpx.AsyncClient(transport=expiration_transport(payload)) as http_client:
        client = PublicMarketDataClient(
            make_settings(),
            http_client=http_client,
            clock=lambda: datetime(2026, 7, 31, 16, 0, tzinfo=UTC),
        )
        with pytest.raises(PublicResponseError, match="duplicate dates"):
            await client.get_option_expirations("AAPL")


@pytest.mark.asyncio
async def test_get_option_expirations_rejects_past_dates() -> None:
    payload = make_payload(expirations=["2026-07-30", "2026-07-31"])
    async with httpx.AsyncClient(transport=expiration_transport(payload)) as http_client:
        client = PublicMarketDataClient(
            make_settings(),
            http_client=http_client,
            clock=lambda: datetime(2026, 7, 31, 16, 0, tzinfo=UTC),
        )
        with pytest.raises(PublicResponseError, match="expired date"):
            await client.get_option_expirations("AAPL")


@pytest.mark.asyncio
async def test_get_option_expirations_propagates_http_error_without_secrets() -> None:
    account_id = "sensitive-account-id"

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/personal/access-tokens"):
            return httpx.Response(200, json={"accessToken": "token"})
        return httpx.Response(503, text="sensitive provider response")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = PublicMarketDataClient(
            make_settings(account_id=account_id),
            http_client=http_client,
        )
        with pytest.raises(PublicHttpError) as exc_info:
            await client.get_option_expirations("AAPL")

    assert exc_info.value.status_code == 503
    assert account_id not in str(exc_info.value)
    assert "sensitive provider response" not in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_option_expirations_refreshes_once_after_401() -> None:
    authentication_count = 0
    authorizations: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal authentication_count
        if request.url.path.endswith("/personal/access-tokens"):
            authentication_count += 1
            return httpx.Response(
                200,
                json={"accessToken": f"token-{authentication_count}"},
            )

        authorizations.append(request.headers["Authorization"])
        if request.headers["Authorization"] == "Bearer token-1":
            return httpx.Response(401)
        return httpx.Response(200, json=make_payload())

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        expirations = await PublicMarketDataClient(
            make_settings(),
            http_client=http_client,
            clock=lambda: datetime(2026, 7, 31, 16, 0, tzinfo=UTC),
        ).get_option_expirations("AAPL")

    assert expirations[0].dte == 0
    assert authentication_count == 2
    assert authorizations == ["Bearer token-1", "Bearer token-2"]


@pytest.mark.asyncio
async def test_get_option_expirations_rejects_blank_symbol_before_network_call() -> None:
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        return httpx.Response(500)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = PublicMarketDataClient(make_settings(), http_client=http_client)
        with pytest.raises(ValueError, match="symbol is required"):
            await client.get_option_expirations("   ")

    assert request_count == 0
