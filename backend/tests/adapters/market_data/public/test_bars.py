from datetime import UTC, datetime
from decimal import Decimal

import httpx
import pytest

from scalper.adapters.market_data.public.client import PublicMarketDataClient
from scalper.adapters.market_data.public.errors import PublicHttpError, PublicResponseError
from scalper.core.config import Settings


def make_settings() -> Settings:
    return Settings(
        _env_file=None,
        public_api_base_url="https://api.public.test",
        public_api_secret="test-secret",
        public_account_id="sensitive-account-id",
        public_max_retries=0,
    )


def make_bar(
    timestamp: object,
    *,
    open_price: object = "150.10",
    high: object = "150.40",
    low: object = "150.00",
    close: object = "150.30",
    volume: object = 1234,
) -> dict[str, object]:
    return {
        "timestamp": timestamp,
        "open": open_price,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
    }


def make_payload(*bars: dict[str, object], symbol: str = "AAPL") -> dict[str, object]:
    return {
        "symbol": symbol,
        "period": "DAY",
        "regularMarket": {
            "expectedBars": len(bars),
            "bars": list(bars),
        },
        "preMarket": {"expectedBars": 0, "bars": []},
        "afterMarket": {"expectedBars": 0, "bars": []},
    }


def bars_transport(payload: object) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/personal/access-tokens"):
            return httpx.Response(200, json={"accessToken": "token"})
        return httpx.Response(200, json=payload)

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_get_bars_maps_completed_regular_session_bars() -> None:
    received_at = datetime(2026, 7, 31, 13, 42, tzinfo=UTC)
    market_requests: list[httpx.Request] = []
    payload = make_payload(
        make_bar("2026-07-31T13:35:00Z", open_price="150.30", close="150.35"),
        make_bar("2026-07-31T13:30:00Z"),
        make_bar("2026-07-31T13:40:00Z", close="150.50"),
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/personal/access-tokens"):
            return httpx.Response(200, json={"accessToken": "bars-token"})
        market_requests.append(request)
        return httpx.Response(200, json=payload)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = PublicMarketDataClient(
            make_settings(),
            http_client=http_client,
            clock=lambda: received_at,
        )
        bars = await client.get_bars("aapl", "5m")

    request = market_requests[0]
    assert request.method == "GET"
    assert request.url.path == "/userapigateway/historicdata/EQUITY/AAPL/DAY/FIVE_MINUTES"
    assert dict(request.url.params) == {"tradingSessionToggle": "REGULAR_HOURS"}
    assert request.headers["Authorization"] == "Bearer bars-token"
    assert "sensitive-account-id" not in str(request.url)

    assert len(bars) == 2
    first, second = bars
    assert first.symbol == "AAPL"
    assert first.timeframe == "5m"
    assert first.open_time == datetime(2026, 7, 31, 13, 30, tzinfo=UTC)
    assert first.close_time == datetime(2026, 7, 31, 13, 35, tzinfo=UTC)
    assert first.open == Decimal("150.10")
    assert first.high == Decimal("150.40")
    assert first.low == Decimal("150.00")
    assert first.close == Decimal("150.30")
    assert first.volume == 1234
    assert first.is_complete is True
    assert second.open_time == datetime(2026, 7, 31, 13, 35, tzinfo=UTC)


@pytest.mark.asyncio
async def test_get_bars_filters_locally_by_complete_interval_bounds() -> None:
    payload = make_payload(
        make_bar("2026-07-31T13:30:00Z"),
        make_bar("2026-07-31T13:35:00Z"),
        make_bar("2026-07-31T13:40:00Z"),
    )
    received_at = datetime(2026, 7, 31, 14, 0, tzinfo=UTC)

    async with httpx.AsyncClient(transport=bars_transport(payload)) as http_client:
        client = PublicMarketDataClient(
            make_settings(),
            http_client=http_client,
            clock=lambda: received_at,
        )
        bars = await client.get_bars(
            "AAPL",
            "FIVE_MINUTES",
            start=datetime(2026, 7, 31, 13, 35, tzinfo=UTC),
            end=datetime(2026, 7, 31, 13, 45, tzinfo=UTC),
        )

    assert [bar.open_time for bar in bars] == [
        datetime(2026, 7, 31, 13, 35, tzinfo=UTC),
        datetime(2026, 7, 31, 13, 40, tzinfo=UTC),
    ]


@pytest.mark.asyncio
async def test_get_bars_preserves_decimal_precision() -> None:
    payload = make_payload(
        make_bar(
            "2026-07-31T13:30:00Z",
            open_price="0.100000000000000001",
            high="0.100000000000000004",
            low="0.100000000000000000",
            close="0.100000000000000003",
        )
    )

    async with httpx.AsyncClient(transport=bars_transport(payload)) as http_client:
        bars = await PublicMarketDataClient(
            make_settings(),
            http_client=http_client,
            clock=lambda: datetime(2026, 7, 31, 14, 0, tzinfo=UTC),
        ).get_bars("AAPL", "5min")

    assert bars[0].open == Decimal("0.100000000000000001")
    assert bars[0].close == Decimal("0.100000000000000003")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("timestamp", "bad"),
        ("timestamp", "2026-07-31T13:30:00"),
        ("open", "bad"),
        ("high", "NaN"),
        ("low", -1),
        ("volume", -1),
    ],
)
async def test_get_bars_rejects_malformed_provider_fields(field: str, value: object) -> None:
    bar = make_bar("2026-07-31T13:30:00Z")
    bar[field] = value
    payload = make_payload(bar)

    async with httpx.AsyncClient(transport=bars_transport(payload)) as http_client:
        client = PublicMarketDataClient(make_settings(), http_client=http_client)
        with pytest.raises(PublicResponseError, match="response was invalid"):
            await client.get_bars("AAPL", "5m")


@pytest.mark.asyncio
async def test_get_bars_uses_canonical_ohlc_validation() -> None:
    payload = make_payload(
        make_bar(
            "2026-07-31T13:30:00Z",
            open_price="150.10",
            high="150.20",
            low="150.00",
            close="150.30",
        )
    )

    async with httpx.AsyncClient(transport=bars_transport(payload)) as http_client:
        client = PublicMarketDataClient(
            make_settings(),
            http_client=http_client,
            clock=lambda: datetime(2026, 7, 31, 14, 0, tzinfo=UTC),
        )
        with pytest.raises(PublicResponseError, match="response was unusable") as exc_info:
            await client.get_bars("AAPL", "5m")

    assert exc_info.value.__cause__ is not None
    assert "bar high is inconsistent" in str(exc_info.value.__cause__)


@pytest.mark.asyncio
async def test_get_bars_rejects_wrong_symbol_period_or_duplicate_timestamp() -> None:
    payloads = (
        make_payload(make_bar("2026-07-31T13:30:00Z"), symbol="MSFT"),
        {
            **make_payload(make_bar("2026-07-31T13:30:00Z")),
            "period": "WEEK",
        },
        make_payload(
            make_bar("2026-07-31T13:30:00Z"),
            make_bar("2026-07-31T13:30:00Z"),
        ),
    )

    for payload in payloads:
        async with httpx.AsyncClient(transport=bars_transport(payload)) as http_client:
            client = PublicMarketDataClient(
                make_settings(),
                http_client=http_client,
                clock=lambda: datetime(2026, 7, 31, 14, 0, tzinfo=UTC),
            )
            with pytest.raises(PublicResponseError):
                await client.get_bars("AAPL", "5m")


@pytest.mark.asyncio
async def test_get_bars_propagates_http_error_without_sensitive_content() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/personal/access-tokens"):
            return httpx.Response(200, json={"accessToken": "token"})
        return httpx.Response(503, text="sensitive provider response")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = PublicMarketDataClient(make_settings(), http_client=http_client)
        with pytest.raises(PublicHttpError) as exc_info:
            await client.get_bars("AAPL", "5m")

    assert exc_info.value.status_code == 503
    assert "sensitive-account-id" not in str(exc_info.value)
    assert "sensitive provider response" not in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_bars_refreshes_once_after_401() -> None:
    authentication_count = 0
    authorizations: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal authentication_count
        if request.url.path.endswith("/personal/access-tokens"):
            authentication_count += 1
            return httpx.Response(200, json={"accessToken": f"token-{authentication_count}"})
        authorizations.append(request.headers["Authorization"])
        if request.headers["Authorization"] == "Bearer token-1":
            return httpx.Response(401)
        return httpx.Response(200, json=make_payload())

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        bars = await PublicMarketDataClient(make_settings(), http_client=http_client).get_bars(
            "AAPL", "5m"
        )

    assert bars == ()
    assert authentication_count == 2
    assert authorizations == ["Bearer token-1", "Bearer token-2"]


@pytest.mark.asyncio
async def test_get_bars_rejects_unsupported_timeframe_and_naive_bound_before_network() -> None:
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        return httpx.Response(500)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = PublicMarketDataClient(make_settings(), http_client=http_client)

        with pytest.raises(ValueError, match="five-minute"):
            await client.get_bars("AAPL", "15m")

        with pytest.raises(ValueError, match="timezone-aware"):
            await client.get_bars(
                "AAPL",
                "5m",
                start=datetime(2026, 7, 31, 9, 30),
            )

    assert request_count == 0


@pytest.mark.asyncio
async def test_get_bars_rejects_end_not_after_start_before_network_call() -> None:
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        return httpx.Response(500)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = PublicMarketDataClient(make_settings(), http_client=http_client)
        with pytest.raises(ValueError, match="end must be after start"):
            await client.get_bars(
                "AAPL",
                "5m",
                start=datetime(2026, 7, 31, 14, 0, tzinfo=UTC),
                end=datetime(2026, 7, 31, 14, 0, tzinfo=UTC),
            )

    assert request_count == 0
