import json
from datetime import UTC, date, datetime
from decimal import Decimal

import httpx
import pytest

from scalper.adapters.market_data.public.client import PublicMarketDataClient
from scalper.adapters.market_data.public.errors import (
    PublicHttpError,
    PublicResponseError,
)
from scalper.core.config import Settings
from scalper.core.enums import OptionRight

EXPIRATION = date(2026, 8, 7)


def make_settings(*, account_id: str = "test-account") -> Settings:
    return Settings(
        _env_file=None,
        public_api_base_url="https://api.public.test",
        public_api_secret="test-secret",
        public_account_id=account_id,
        public_max_retries=0,
    )


def osi_symbol(*, right: str, strike: str, expiration: date = EXPIRATION) -> str:
    strike_code = int(Decimal(strike) * 1000)
    return f"AAPL{expiration:%y%m%d}{right}{strike_code:08d}"


def make_contract(
    *,
    right: str = "C",
    strike: str = "150",
    symbol: str | None = None,
    outcome: str = "SUCCESS",
    bid: object = "1.20",
    ask: object = "1.25",
    bid_size: object = 10,
    ask_size: object = 12,
    bid_timestamp: object = "2026-08-01T12:00:02Z",
    ask_timestamp: object = "2026-08-01T12:00:01Z",
    volume: object = 100,
    open_interest: object = 500,
    greeks: object = None,
    instrument_type: str = "OPTION",
) -> dict[str, object]:
    if symbol is None:
        symbol = osi_symbol(right=right, strike=strike)
    if greeks is None:
        greeks = {
            "delta": "0.50" if right == "C" else "-0.50",
            "gamma": "0.020",
            "theta": "-0.100",
            "vega": "0.200",
            "rho": "0.010",
            "impliedVolatility": "0.400",
        }

    return {
        "instrument": {
            "symbol": symbol,
            "type": instrument_type,
        },
        "outcome": outcome,
        "bid": bid,
        "ask": ask,
        "bidSize": bid_size,
        "askSize": ask_size,
        "bidTimestamp": bid_timestamp,
        "askTimestamp": ask_timestamp,
        "volume": volume,
        "openInterest": open_interest,
        "optionDetails": {
            "strikePrice": strike,
            "midPrice": "1.225",
            "greeks": greeks,
        },
    }


def make_payload(
    *,
    base_symbol: str = "AAPL",
    calls: object = None,
    puts: object = None,
) -> dict[str, object]:
    if calls is None:
        calls = [
            make_contract(
                right="C",
                strike="155",
                bid="0.80",
                ask="0.85",
                bid_timestamp="2026-08-01T12:00:04Z",
                ask_timestamp="2026-08-01T12:00:03Z",
            ),
            make_contract(right="C", strike="150"),
        ]
    if puts is None:
        puts = [
            make_contract(
                right="P",
                strike="145",
                bid="0.70",
                ask="0.75",
                bid_timestamp="2026-08-01T12:00:06Z",
                ask_timestamp="2026-08-01T12:00:05Z",
            )
        ]

    return {
        "baseSymbol": base_symbol,
        "calls": calls,
        "puts": puts,
    }


def chain_transport(payload: object) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/personal/access-tokens"):
            return httpx.Response(200, json={"accessToken": "token"})
        return httpx.Response(200, json=payload)

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_get_option_chain_maps_exact_public_contracts() -> None:
    received_at = datetime(2026, 8, 1, 12, 1, tzinfo=UTC)
    market_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/personal/access-tokens"):
            return httpx.Response(200, json={"accessToken": "chain-token"})
        market_requests.append(request)
        return httpx.Response(200, json=make_payload())

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = PublicMarketDataClient(
            make_settings(),
            http_client=http_client,
            clock=lambda: received_at,
        )
        chain = await client.get_option_chain("aapl", EXPIRATION)

    request = market_requests[0]
    assert request.method == "POST"
    assert request.url.path == "/userapigateway/marketdata/test-account/option-chain"
    assert request.headers["Authorization"] == "Bearer chain-token"
    assert json.loads(request.content.decode("utf-8")) == {
        "instrument": {"symbol": "AAPL", "type": "EQUITY"},
        "expirationDate": "2026-08-07",
    }

    assert chain.underlying == "AAPL"
    assert chain.expiration == EXPIRATION
    assert chain.received_timestamp == received_at
    assert chain.source_timestamp == datetime(2026, 8, 1, 12, 0, 1, tzinfo=UTC)

    assert [contract.strike for contract in chain.calls] == [
        Decimal("150"),
        Decimal("155"),
    ]
    call = chain.calls[0]
    assert call.symbol == "AAPL260807C00150000"
    assert call.right is OptionRight.CALL
    assert call.quote.bid == Decimal("1.20")
    assert call.quote.ask == Decimal("1.25")
    assert call.quote.bid_size == 10
    assert call.quote.ask_size == 12
    assert call.volume == 100
    assert call.open_interest == 500
    assert call.greeks is not None
    assert call.greeks.delta == Decimal("0.50")
    assert call.greeks.implied_volatility == Decimal("0.400")
    assert call.tick_size is None

    put = chain.puts[0]
    assert put.symbol == "AAPL260807P00145000"
    assert put.right is OptionRight.PUT
    assert put.greeks is not None
    assert put.greeks.delta == Decimal("-0.50")


@pytest.mark.asyncio
async def test_get_option_chain_allows_missing_optional_market_data() -> None:
    contract = make_contract(
        right="C",
        strike="150",
        bid_size=None,
        ask_size=None,
        volume=None,
        open_interest=None,
        greeks=None,
    )
    option_details = contract["optionDetails"]
    assert isinstance(option_details, dict)
    option_details["greeks"] = None
    payload = make_payload(calls=[contract], puts=[])

    async with httpx.AsyncClient(transport=chain_transport(payload)) as http_client:
        chain = await PublicMarketDataClient(
            make_settings(),
            http_client=http_client,
            clock=lambda: datetime(2026, 8, 1, 12, 1, tzinfo=UTC),
        ).get_option_chain("AAPL", EXPIRATION)

    mapped = chain.calls[0]
    assert mapped.quote.bid_size is None
    assert mapped.quote.ask_size is None
    assert mapped.volume is None
    assert mapped.open_interest is None
    assert mapped.greeks is None


@pytest.mark.asyncio
async def test_get_option_chain_maps_partial_greeks() -> None:
    contract = make_contract(
        right="C",
        strike="150",
        greeks={"delta": "0.55"},
    )
    payload = make_payload(calls=[contract], puts=[])

    async with httpx.AsyncClient(transport=chain_transport(payload)) as http_client:
        chain = await PublicMarketDataClient(
            make_settings(),
            http_client=http_client,
            clock=lambda: datetime(2026, 8, 1, 12, 1, tzinfo=UTC),
        ).get_option_chain("AAPL", EXPIRATION)

    greeks = chain.calls[0].greeks
    assert greeks is not None
    assert greeks.delta == Decimal("0.55")
    assert greeks.gamma is None
    assert greeks.implied_volatility is None


@pytest.mark.asyncio
async def test_get_option_chain_returns_empty_chain() -> None:
    received_at = datetime(2026, 8, 1, 12, 1, tzinfo=UTC)
    payload = make_payload(calls=[], puts=[])

    async with httpx.AsyncClient(transport=chain_transport(payload)) as http_client:
        chain = await PublicMarketDataClient(
            make_settings(),
            http_client=http_client,
            clock=lambda: received_at,
        ).get_option_chain("AAPL", EXPIRATION)

    assert chain.calls == ()
    assert chain.puts == ()
    assert chain.source_timestamp == received_at


@pytest.mark.asyncio
async def test_get_option_chain_preserves_decimal_precision() -> None:
    contract = make_contract(
        right="C",
        strike="150.125",
        bid="0.100000000000000001",
        ask="0.100000000000000002",
        greeks={
            "delta": "0.500000000000000001",
            "impliedVolatility": "0.400000000000000001",
        },
    )
    payload = make_payload(calls=[contract], puts=[])

    async with httpx.AsyncClient(transport=chain_transport(payload)) as http_client:
        chain = await PublicMarketDataClient(
            make_settings(),
            http_client=http_client,
            clock=lambda: datetime(2026, 8, 1, 12, 1, tzinfo=UTC),
        ).get_option_chain("AAPL", EXPIRATION)

    mapped = chain.calls[0]
    assert mapped.strike == Decimal("150.125")
    assert mapped.quote.bid == Decimal("0.100000000000000001")
    assert mapped.quote.ask == Decimal("0.100000000000000002")
    assert mapped.greeks is not None
    assert mapped.greeks.delta == Decimal("0.500000000000000001")


@pytest.mark.asyncio
@pytest.mark.parametrize("missing_field", ["baseSymbol", "calls", "puts"])
async def test_get_option_chain_rejects_missing_top_level_fields(
    missing_field: str,
) -> None:
    payload = make_payload()
    payload.pop(missing_field)

    async with httpx.AsyncClient(transport=chain_transport(payload)) as http_client:
        client = PublicMarketDataClient(make_settings(), http_client=http_client)
        with pytest.raises(PublicResponseError, match="response was invalid"):
            await client.get_option_chain("AAPL", EXPIRATION)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field_path", "value"),
    [
        (("instrument", "type"), "EQUITY"),
        (("bid",), "bad"),
        (("ask",), "NaN"),
        (("bidSize",), -1),
        (("askSize",), "bad"),
        (("bidTimestamp",), "bad"),
        (("askTimestamp",), "2026-08-01T12:00:01"),
        (("volume",), -1),
        (("openInterest",), -1),
        (("optionDetails", "strikePrice"), "bad"),
        (("optionDetails", "greeks", "impliedVolatility"), -1),
    ],
)
async def test_get_option_chain_rejects_malformed_contract_fields(
    field_path: tuple[str, ...],
    value: object,
) -> None:
    contract = make_contract()
    target: dict[str, object] = contract
    for key in field_path[:-1]:
        nested = target[key]
        assert isinstance(nested, dict)
        target = nested
    target[field_path[-1]] = value
    payload = make_payload(calls=[contract], puts=[])

    async with httpx.AsyncClient(transport=chain_transport(payload)) as http_client:
        client = PublicMarketDataClient(make_settings(), http_client=http_client)
        with pytest.raises(PublicResponseError, match="response was invalid"):
            await client.get_option_chain("AAPL", EXPIRATION)


@pytest.mark.asyncio
async def test_get_option_chain_rejects_wrong_base_symbol() -> None:
    payload = make_payload(base_symbol="MSFT")
    async with httpx.AsyncClient(transport=chain_transport(payload)) as http_client:
        client = PublicMarketDataClient(make_settings(), http_client=http_client)
        with pytest.raises(PublicResponseError, match="symbol did not match"):
            await client.get_option_chain("AAPL", EXPIRATION)


@pytest.mark.asyncio
async def test_get_option_chain_rejects_unsuccessful_contract() -> None:
    payload = make_payload(
        calls=[make_contract(outcome="FAILURE")],
        puts=[],
    )
    async with httpx.AsyncClient(transport=chain_transport(payload)) as http_client:
        client = PublicMarketDataClient(make_settings(), http_client=http_client)
        with pytest.raises(PublicResponseError, match="unsuccessful contract"):
            await client.get_option_chain("AAPL", EXPIRATION)


@pytest.mark.asyncio
async def test_get_option_chain_rejects_duplicate_symbols() -> None:
    contract = make_contract()
    payload = make_payload(calls=[contract, contract.copy()], puts=[])

    async with httpx.AsyncClient(transport=chain_transport(payload)) as http_client:
        client = PublicMarketDataClient(make_settings(), http_client=http_client)
        with pytest.raises(PublicResponseError, match="duplicate option symbols"):
            await client.get_option_chain("AAPL", EXPIRATION)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "symbol",
    [
        "BAD",
        "AAPL260832C00150000",
        "AAPL260807X00150000",
        "AAPL260807C00ABC000",
        "AAPL260807C00000000",
    ],
)
async def test_get_option_chain_rejects_invalid_osi_symbols(symbol: str) -> None:
    payload = make_payload(
        calls=[make_contract(symbol=symbol)],
        puts=[],
    )
    async with httpx.AsyncClient(transport=chain_transport(payload)) as http_client:
        client = PublicMarketDataClient(make_settings(), http_client=http_client)
        with pytest.raises(PublicResponseError, match="invalid option symbol"):
            await client.get_option_chain("AAPL", EXPIRATION)


@pytest.mark.asyncio
async def test_get_option_chain_rejects_osi_expiration_mismatch() -> None:
    wrong_expiration = date(2026, 8, 14)
    payload = make_payload(
        calls=[
            make_contract(
                symbol=osi_symbol(
                    right="C",
                    strike="150",
                    expiration=wrong_expiration,
                )
            )
        ],
        puts=[],
    )
    async with httpx.AsyncClient(transport=chain_transport(payload)) as http_client:
        client = PublicMarketDataClient(make_settings(), http_client=http_client)
        with pytest.raises(PublicResponseError, match="expiration did not match"):
            await client.get_option_chain("AAPL", EXPIRATION)


@pytest.mark.asyncio
async def test_get_option_chain_rejects_osi_right_mismatch() -> None:
    payload = make_payload(
        calls=[make_contract(symbol=osi_symbol(right="P", strike="150"))],
        puts=[],
    )
    async with httpx.AsyncClient(transport=chain_transport(payload)) as http_client:
        client = PublicMarketDataClient(make_settings(), http_client=http_client)
        with pytest.raises(PublicResponseError, match="right did not match"):
            await client.get_option_chain("AAPL", EXPIRATION)


@pytest.mark.asyncio
async def test_get_option_chain_rejects_osi_strike_mismatch() -> None:
    payload = make_payload(
        calls=[
            make_contract(
                strike="150",
                symbol=osi_symbol(right="C", strike="151"),
            )
        ],
        puts=[],
    )
    async with httpx.AsyncClient(transport=chain_transport(payload)) as http_client:
        client = PublicMarketDataClient(make_settings(), http_client=http_client)
        with pytest.raises(PublicResponseError, match="strike did not match"):
            await client.get_option_chain("AAPL", EXPIRATION)


@pytest.mark.asyncio
async def test_get_option_chain_uses_canonical_crossed_quote_validation() -> None:
    payload = make_payload(
        calls=[make_contract(bid="1.30", ask="1.25")],
        puts=[],
    )
    async with httpx.AsyncClient(transport=chain_transport(payload)) as http_client:
        client = PublicMarketDataClient(make_settings(), http_client=http_client)
        with pytest.raises(PublicResponseError, match="response was unusable") as exc_info:
            await client.get_option_chain("AAPL", EXPIRATION)

    assert exc_info.value.__cause__ is not None
    assert "crossed quote" in str(exc_info.value.__cause__)


@pytest.mark.asyncio
async def test_get_option_chain_rejects_past_expiration_before_network_call() -> None:
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        return httpx.Response(500)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = PublicMarketDataClient(
            make_settings(),
            http_client=http_client,
            clock=lambda: datetime(2026, 8, 1, 14, 0, tzinfo=UTC),
        )
        with pytest.raises(ValueError, match="expiration cannot be in the past"):
            await client.get_option_chain("AAPL", date(2026, 7, 31))

    assert request_count == 0


@pytest.mark.asyncio
async def test_get_option_chain_rejects_datetime_expiration_before_network_call() -> None:
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        return httpx.Response(500)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = PublicMarketDataClient(make_settings(), http_client=http_client)
        with pytest.raises(TypeError, match="expiration must be a date"):
            await client.get_option_chain(
                "AAPL",
                datetime(2026, 8, 7, tzinfo=UTC),  # type: ignore[arg-type]
            )

    assert request_count == 0


@pytest.mark.asyncio
async def test_get_option_chain_rejects_blank_symbol_before_network_call() -> None:
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        return httpx.Response(500)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = PublicMarketDataClient(make_settings(), http_client=http_client)
        with pytest.raises(ValueError, match="symbol is required"):
            await client.get_option_chain("   ", EXPIRATION)

    assert request_count == 0


@pytest.mark.asyncio
async def test_get_option_chain_propagates_http_error_without_secrets() -> None:
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
            await client.get_option_chain("AAPL", EXPIRATION)

    assert exc_info.value.status_code == 503
    assert account_id not in str(exc_info.value)
    assert "sensitive provider response" not in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_option_chain_refreshes_once_after_401() -> None:
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
        chain = await PublicMarketDataClient(
            make_settings(),
            http_client=http_client,
            clock=lambda: datetime(2026, 8, 1, 12, 1, tzinfo=UTC),
        ).get_option_chain("AAPL", EXPIRATION)

    assert chain.calls
    assert authentication_count == 2
    assert authorizations == ["Bearer token-1", "Bearer token-2"]
