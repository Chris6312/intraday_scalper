import json
from datetime import UTC, datetime
from decimal import Decimal

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


def make_quote_payload(
    *,
    symbol: str = "AAPL",
    outcome: str = "SUCCESS",
    bid: object = "150.20",
    ask: object = "150.30",
    bid_size: object = 100,
    ask_size: object = 200,
    bid_timestamp: object = "2026-07-31T15:59:02Z",
    ask_timestamp: object = "2026-07-31T15:59:01Z",
) -> dict[str, object]:
    return {
        "quotes": [
            {
                "instrument": {"symbol": symbol, "type": "EQUITY"},
                "outcome": outcome,
                "bid": bid,
                "ask": ask,
                "bidSize": bid_size,
                "askSize": ask_size,
                "bidTimestamp": bid_timestamp,
                "askTimestamp": ask_timestamp,
            }
        ]
    }


def quote_handler(payload: object) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/personal/access-tokens"):
            return httpx.Response(200, json={"accessToken": "token"})
        return httpx.Response(200, json=payload)

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_get_quote_maps_public_equity_quote_to_canonical_quote() -> None:
    received_at = datetime(2026, 7, 31, 16, 0, tzinfo=UTC)
    market_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/personal/access-tokens"):
            return httpx.Response(200, json={"accessToken": "quote-token"})
        market_requests.append(request)
        return httpx.Response(200, json=make_quote_payload())

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = PublicMarketDataClient(
            make_settings(),
            http_client=http_client,
            clock=lambda: received_at,
        )
        quote = await client.get_quote("aapl")

    request = market_requests[0]
    assert request.method == "POST"
    assert request.url.path == "/userapigateway/marketdata/test-account/quotes"
    assert request.headers["Authorization"] == "Bearer quote-token"
    assert json.loads(request.content.decode("utf-8")) == {
        "instruments": [{"symbol": "AAPL", "type": "EQUITY"}]
    }
    assert quote.symbol == "AAPL"
    assert quote.bid == Decimal("150.20")
    assert quote.ask == Decimal("150.30")
    assert quote.bid_size == 100
    assert quote.ask_size == 200
    # The whole two-sided quote is only as fresh as its older side.
    assert quote.source_timestamp == datetime(2026, 7, 31, 15, 59, 1, tzinfo=UTC)
    assert quote.received_timestamp == received_at


@pytest.mark.asyncio
async def test_get_quote_preserves_decimal_precision() -> None:
    payload = make_quote_payload(
        bid="0.100000000000000001",
        ask="0.100000000000000002",
    )
    async with httpx.AsyncClient(transport=quote_handler(payload)) as http_client:
        quote = await PublicMarketDataClient(make_settings(), http_client=http_client).get_quote(
            "AAPL"
        )

    assert quote.bid == Decimal("0.100000000000000001")
    assert quote.ask == Decimal("0.100000000000000002")


@pytest.mark.asyncio
@pytest.mark.parametrize("missing_field", ["bid", "ask", "bidTimestamp", "askTimestamp"])
async def test_get_quote_rejects_missing_required_fields(missing_field: str) -> None:
    payload = make_quote_payload()
    quotes = payload["quotes"]
    assert isinstance(quotes, list)
    quote = quotes[0]
    assert isinstance(quote, dict)
    quote.pop(missing_field)

    async with httpx.AsyncClient(transport=quote_handler(payload)) as http_client:
        client = PublicMarketDataClient(make_settings(), http_client=http_client)
        with pytest.raises(PublicResponseError, match="response was invalid"):
            await client.get_quote("AAPL")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field", "value"),
    [("bid", "bad"), ("ask", "NaN"), ("bidSize", -1), ("askSize", "bad")],
)
async def test_get_quote_rejects_malformed_numeric_values(field: str, value: object) -> None:
    payload = make_quote_payload()
    quotes = payload["quotes"]
    assert isinstance(quotes, list)
    quote = quotes[0]
    assert isinstance(quote, dict)
    quote[field] = value

    async with httpx.AsyncClient(transport=quote_handler(payload)) as http_client:
        client = PublicMarketDataClient(make_settings(), http_client=http_client)
        with pytest.raises(PublicResponseError, match="response was invalid"):
            await client.get_quote("AAPL")


@pytest.mark.asyncio
@pytest.mark.parametrize("timestamp", ["bad", "2026-07-31T15:59:01"])
async def test_get_quote_rejects_malformed_or_naive_timestamps(timestamp: str) -> None:
    payload = make_quote_payload(ask_timestamp=timestamp)
    async with httpx.AsyncClient(transport=quote_handler(payload)) as http_client:
        client = PublicMarketDataClient(make_settings(), http_client=http_client)
        with pytest.raises(PublicResponseError, match="response was invalid"):
            await client.get_quote("AAPL")


@pytest.mark.asyncio
async def test_get_quote_uses_canonical_validation_for_crossed_market() -> None:
    payload = make_quote_payload(bid="150.40", ask="150.30")
    async with httpx.AsyncClient(transport=quote_handler(payload)) as http_client:
        client = PublicMarketDataClient(make_settings(), http_client=http_client)
        with pytest.raises(PublicResponseError, match="response was unusable") as exc_info:
            await client.get_quote("AAPL")

    assert exc_info.value.__cause__ is not None
    assert "crossed quote" in str(exc_info.value.__cause__)


@pytest.mark.asyncio
async def test_get_quote_propagates_http_error_without_body_or_account_id() -> None:
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
            await client.get_quote("AAPL")

    assert exc_info.value.status_code == 503
    assert account_id not in str(exc_info.value)
    assert "sensitive provider response" not in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_quote_refreshes_once_after_401() -> None:
    authentication_count = 0
    quote_authorizations: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal authentication_count
        if request.url.path.endswith("/personal/access-tokens"):
            authentication_count += 1
            return httpx.Response(200, json={"accessToken": f"token-{authentication_count}"})

        quote_authorizations.append(request.headers["Authorization"])
        if request.headers["Authorization"] == "Bearer token-1":
            return httpx.Response(401)
        return httpx.Response(200, json=make_quote_payload())

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        quote = await PublicMarketDataClient(make_settings(), http_client=http_client).get_quote(
            "AAPL"
        )

    assert quote.symbol == "AAPL"
    assert authentication_count == 2
    assert quote_authorizations == ["Bearer token-1", "Bearer token-2"]


@pytest.mark.asyncio
async def test_get_quote_rejects_unsuccessful_or_wrong_symbol_payload() -> None:
    for payload in (
        make_quote_payload(outcome="FAILURE"),
        make_quote_payload(symbol="MSFT"),
    ):
        async with httpx.AsyncClient(transport=quote_handler(payload)) as http_client:
            client = PublicMarketDataClient(make_settings(), http_client=http_client)
            with pytest.raises(PublicResponseError):
                await client.get_quote("AAPL")
