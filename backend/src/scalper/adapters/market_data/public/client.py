import asyncio
from collections.abc import Awaitable, Callable, Mapping
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from email.utils import parsedate_to_datetime
from math import ldexp
from types import TracebackType
from typing import Any, Self

import httpx
from pydantic import SecretStr, ValidationError

from scalper.core.config import Settings
from scalper.core.enums import OptionRight
from scalper.core.time import EASTERN, require_aware, utc_now
from scalper.domain.market import (
    Bar,
    OptionChain,
    OptionContract,
    OptionExpiration,
    OptionGreeks,
    Quote,
)

from .errors import (
    PublicAuthenticationError,
    PublicConfigurationError,
    PublicHttpError,
    PublicRateLimitError,
    PublicResponseError,
    PublicTransportError,
)
from .models import (
    PublicAccessTokenResponse,
    PublicBarsResponse,
    PublicOptionChainContractPayload,
    PublicOptionChainResponse,
    PublicOptionExpirationsResponse,
    PublicQuotesResponse,
)

Clock = Callable[[], datetime]
Sleeper = Callable[[float], Awaitable[None]]


class PublicMarketDataClient:
    """Authenticated HTTP client restricted to Public market-data requests."""

    _AUTH_PATH = "/userapiauthservice/personal/access-tokens"
    _USER_AGENT = "options-intraday-scalper/0.1.0"
    _FIVE_MINUTE_TIMEFRAME = "5m"
    _FIVE_MINUTE_DURATION = timedelta(minutes=5)

    def __init__(
        self,
        settings: Settings,
        *,
        http_client: httpx.AsyncClient | None = None,
        clock: Clock = utc_now,
        sleeper: Sleeper = asyncio.sleep,
    ) -> None:
        self._base_url = self._validate_base_url(settings.public_api_base_url)
        self._secret = self._read_required_secret(
            settings.public_api_secret,
            "PUBLIC_API_SECRET",
        )
        self._account_id = self._read_required_secret(
            settings.public_account_id,
            "PUBLIC_ACCOUNT_ID",
        )

        self._token_ttl_minutes = settings.public_access_token_ttl_minutes
        self._token_refresh_leeway_seconds = settings.public_token_refresh_leeway_seconds
        self._max_retries = settings.public_max_retries
        self._retry_base_delay_seconds: float = float(settings.public_retry_base_delay_seconds)

        self._clock = clock
        self._sleeper = sleeper
        self._token_lock = asyncio.Lock()

        self._access_token: str | None = None
        self._access_token_expires_at: datetime | None = None

        timeout = httpx.Timeout(
            connect=settings.public_connect_timeout_seconds,
            read=settings.public_read_timeout_seconds,
            write=settings.public_write_timeout_seconds,
            pool=settings.public_pool_timeout_seconds,
        )

        self._owns_http_client = http_client is None
        self._http_client = http_client or httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=False,
        )

    @property
    def account_id(self) -> str:
        return self._account_id

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_http_client:
            await self._http_client.aclose()

    async def get_access_token(self) -> str:
        if self._has_fresh_access_token():
            assert self._access_token is not None
            return self._access_token

        async with self._token_lock:
            if self._has_fresh_access_token():
                assert self._access_token is not None
                return self._access_token

            access_token = await self._create_access_token()
            issued_at = self._now()

            self._access_token = access_token
            self._access_token_expires_at = issued_at + timedelta(minutes=self._token_ttl_minutes)
            return access_token

    async def get_bars(
        self,
        symbol: str,
        timeframe: str,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> tuple[Bar, ...]:
        """Retrieve completed regular-session five-minute equity bars."""

        normalized_symbol = symbol.strip().upper()
        if not normalized_symbol:
            raise ValueError("symbol is required")

        normalized_timeframe = self._normalize_five_minute_timeframe(timeframe)
        start_utc = self._normalize_optional_bound(start, "start")
        end_utc = self._normalize_optional_bound(end, "end")
        if start_utc is not None and end_utc is not None and end_utc <= start_utc:
            raise ValueError("end must be after start")

        response = await self.request(
            "GET",
            f"/userapigateway/historicdata/EQUITY/{normalized_symbol}/DAY/FIVE_MINUTES",
            params={"tradingSessionToggle": "REGULAR_HOURS"},
        )
        received_timestamp = self._now()

        try:
            payload = response.json()
            bars_response = PublicBarsResponse.model_validate(payload)
        except (ValueError, ValidationError) as exc:
            raise PublicResponseError("Public bars response was invalid") from exc

        if bars_response.symbol.upper() != normalized_symbol:
            raise PublicResponseError("Public bars response symbol did not match the request")

        public_bars = sorted(
            bars_response.regular_market.bars,
            key=lambda bar: bar.timestamp,
        )
        timestamps = [bar.timestamp.astimezone(UTC) for bar in public_bars]
        if len(timestamps) != len(set(timestamps)):
            raise PublicResponseError("Public bars response contained duplicate timestamps")

        canonical_bars: list[Bar] = []
        for public_bar, open_time in zip(public_bars, timestamps, strict=True):
            # Public documents a single bar timestamp but does not label it as open or close.
            # This adapter treats it as the interval open pending a controlled smoke test.
            close_time = open_time + self._FIVE_MINUTE_DURATION

            if close_time > received_timestamp:
                continue
            if start_utc is not None and open_time < start_utc:
                continue
            if end_utc is not None and close_time > end_utc:
                continue

            try:
                canonical_bars.append(
                    Bar(
                        symbol=normalized_symbol,
                        timeframe=normalized_timeframe,
                        open_time=open_time,
                        close_time=close_time,
                        open=public_bar.open,
                        high=public_bar.high,
                        low=public_bar.low,
                        close=public_bar.close,
                        volume=public_bar.volume,
                        is_complete=True,
                    )
                )
            except ValidationError as exc:
                raise PublicResponseError("Public bars response was unusable") from exc

        return tuple(canonical_bars)

    async def get_option_expirations(
        self,
        symbol: str,
    ) -> tuple[OptionExpiration, ...]:
        """Retrieve Public-listed option expirations for one equity."""

        normalized_symbol = symbol.strip().upper()
        if not normalized_symbol:
            raise ValueError("symbol is required")

        response = await self.request(
            "POST",
            f"/userapigateway/marketdata/{self._account_id}/option-expirations",
            json_body={
                "instrument": {
                    "symbol": normalized_symbol,
                    "type": "EQUITY",
                }
            },
        )

        try:
            payload = response.json()
            expiration_response = PublicOptionExpirationsResponse.model_validate(payload)
        except (ValueError, ValidationError) as exc:
            raise PublicResponseError("Public option-expirations response was invalid") from exc

        if expiration_response.base_symbol.upper() != normalized_symbol:
            raise PublicResponseError(
                "Public option-expirations response symbol did not match the request"
            )

        expiration_dates = expiration_response.expirations
        if len(expiration_dates) != len(set(expiration_dates)):
            raise PublicResponseError(
                "Public option-expirations response contained duplicate dates"
            )

        current_eastern_date = self._now().astimezone(EASTERN).date()
        if any(expiration < current_eastern_date for expiration in expiration_dates):
            raise PublicResponseError(
                "Public option-expirations response contained an expired date"
            )

        try:
            return tuple(
                OptionExpiration(
                    underlying=normalized_symbol,
                    expiration=expiration,
                    dte=(expiration - current_eastern_date).days,
                )
                for expiration in sorted(expiration_dates)
            )
        except ValidationError as exc:
            raise PublicResponseError("Public option-expirations response was unusable") from exc

    async def get_option_chain(
        self,
        symbol: str,
        expiration: date,
    ) -> OptionChain:
        """Retrieve one Public-listed option chain."""

        normalized_symbol = symbol.strip().upper()
        if not normalized_symbol:
            raise ValueError("symbol is required")
        if isinstance(expiration, datetime) or not isinstance(expiration, date):
            raise TypeError("expiration must be a date")

        current_eastern_date = self._now().astimezone(EASTERN).date()
        if expiration < current_eastern_date:
            raise ValueError("expiration cannot be in the past")

        response = await self.request(
            "POST",
            f"/userapigateway/marketdata/{self._account_id}/option-chain",
            json_body={
                "instrument": {
                    "symbol": normalized_symbol,
                    "type": "EQUITY",
                },
                "expirationDate": expiration.isoformat(),
            },
        )
        received_timestamp = self._now()

        try:
            payload = response.json()
            chain_response = PublicOptionChainResponse.model_validate(payload)
        except (ValueError, ValidationError) as exc:
            raise PublicResponseError("Public option-chain response was invalid") from exc

        if chain_response.base_symbol.upper() != normalized_symbol:
            raise PublicResponseError(
                "Public option-chain response symbol did not match the request"
            )

        public_contracts = (*chain_response.calls, *chain_response.puts)
        contract_symbols = [contract.instrument.symbol.upper() for contract in public_contracts]
        if len(contract_symbols) != len(set(contract_symbols)):
            raise PublicResponseError(
                "Public option-chain response contained duplicate option symbols"
            )

        calls = tuple(
            sorted(
                (
                    self._map_option_chain_contract(
                        contract,
                        underlying=normalized_symbol,
                        expiration=expiration,
                        right=OptionRight.CALL,
                        received_timestamp=received_timestamp,
                    )
                    for contract in chain_response.calls
                ),
                key=lambda contract: (contract.strike, contract.symbol),
            )
        )
        puts = tuple(
            sorted(
                (
                    self._map_option_chain_contract(
                        contract,
                        underlying=normalized_symbol,
                        expiration=expiration,
                        right=OptionRight.PUT,
                        received_timestamp=received_timestamp,
                    )
                    for contract in chain_response.puts
                ),
                key=lambda contract: (contract.strike, contract.symbol),
            )
        )

        quote_timestamps = [contract.quote.source_timestamp for contract in (*calls, *puts)]
        # Public supplies no chain-level timestamp. Use the oldest mapped quote so the
        # canonical chain never appears fresher than one of its contracts.
        source_timestamp = min(quote_timestamps, default=received_timestamp)

        try:
            return OptionChain(
                underlying=normalized_symbol,
                expiration=expiration,
                calls=calls,
                puts=puts,
                source_timestamp=source_timestamp,
                received_timestamp=received_timestamp,
            )
        except ValidationError as exc:
            raise PublicResponseError("Public option-chain response was unusable") from exc

    async def get_quote(self, symbol: str) -> Quote:
        """Retrieve and map one underlying-equity quote."""

        normalized_symbol = symbol.strip().upper()
        if not normalized_symbol:
            raise ValueError("symbol is required")

        response = await self.request(
            "POST",
            f"/userapigateway/marketdata/{self._account_id}/quotes",
            json_body={
                "instruments": [
                    {
                        "symbol": normalized_symbol,
                        "type": "EQUITY",
                    }
                ]
            },
        )
        received_timestamp = self._now()

        try:
            payload = response.json()
            quote_response = PublicQuotesResponse.model_validate(payload)
        except (ValueError, ValidationError) as exc:
            raise PublicResponseError("Public quote response was invalid") from exc

        matching_quotes = [
            quote
            for quote in quote_response.quotes
            if quote.instrument.symbol.upper() == normalized_symbol
        ]
        if len(matching_quotes) != 1:
            raise PublicResponseError(
                "Public quote response did not contain exactly one requested equity"
            )

        public_quote = matching_quotes[0]
        if public_quote.outcome != "SUCCESS":
            raise PublicResponseError("Public quote request did not succeed")

        # A two-sided canonical quote is only as fresh as its older side.
        source_timestamp = min(
            public_quote.bid_timestamp,
            public_quote.ask_timestamp,
        ).astimezone(UTC)

        try:
            return Quote(
                symbol=public_quote.instrument.symbol.upper(),
                bid=public_quote.bid,
                ask=public_quote.ask,
                bid_size=public_quote.bid_size,
                ask_size=public_quote.ask_size,
                source_timestamp=source_timestamp,
                received_timestamp=received_timestamp,
            )
        except ValidationError as exc:
            raise PublicResponseError("Public quote response was unusable") from exc

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, str | int | float | bool] | None = None,
        json_body: Any = None,
        headers: Mapping[str, str] | None = None,
    ) -> httpx.Response:
        """Send a retryable, authenticated market-data request."""

        access_token = await self.get_access_token()

        response = await self._send_with_retries(
            method,
            path,
            params=params,
            json_body=json_body,
            headers=headers,
            bearer_token=access_token,
            allow_unauthorized=True,
        )

        if response.status_code != 401:
            return response

        await self._invalidate_access_token_if_current(access_token)
        refreshed_token = await self.get_access_token()

        return await self._send_with_retries(
            method,
            path,
            params=params,
            json_body=json_body,
            headers=headers,
            bearer_token=refreshed_token,
            allow_unauthorized=False,
        )

    async def _create_access_token(self) -> str:
        response = await self._send_with_retries(
            "POST",
            self._AUTH_PATH,
            json_body={
                "validityInMinutes": self._token_ttl_minutes,
                "secret": self._secret,
            },
            bearer_token=None,
            allow_unauthorized=False,
        )

        try:
            payload = response.json()
            token_response = PublicAccessTokenResponse.model_validate(payload)
        except (ValueError, ValidationError) as exc:
            raise PublicResponseError("Public authentication response was invalid") from exc

        return token_response.access_token

    async def _invalidate_access_token_if_current(self, access_token: str) -> None:
        async with self._token_lock:
            if self._access_token == access_token:
                self._access_token = None
                self._access_token_expires_at = None

    def _has_fresh_access_token(self) -> bool:
        if self._access_token is None or self._access_token_expires_at is None:
            return False

        refresh_at = self._access_token_expires_at - timedelta(
            seconds=self._token_refresh_leeway_seconds
        )
        return self._now() < refresh_at

    async def _send_with_retries(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, str | int | float | bool] | None = None,
        json_body: Any = None,
        headers: Mapping[str, str] | None = None,
        bearer_token: str | None,
        allow_unauthorized: bool,
    ) -> httpx.Response:
        url = self._build_url(path)

        for attempt in range(self._max_retries + 1):
            request_headers = self._build_headers(headers, bearer_token)
            request_arguments: dict[str, Any] = {
                "headers": request_headers,
            }

            if params is not None:
                request_arguments["params"] = params
            if json_body is not None:
                request_arguments["json"] = json_body

            try:
                response = await self._http_client.request(
                    method,
                    url,
                    **request_arguments,
                )
            except httpx.TransportError as exc:
                if attempt >= self._max_retries:
                    raise PublicTransportError("Public API transport request failed") from exc

                await self._sleeper(self._backoff_delay(attempt))
                continue

            if self._is_retryable_status(response.status_code) and attempt < self._max_retries:
                await self._sleeper(self._retry_delay(response, attempt))
                continue

            if response.status_code == 401 and allow_unauthorized:
                return response

            self._raise_for_status(response)
            return response

        raise AssertionError("Public retry loop exited unexpectedly")

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.status_code < 400:
            return

        if response.status_code == 401:
            raise PublicAuthenticationError("Public API authentication failed")

        if response.status_code == 429:
            raise PublicRateLimitError(self._parse_retry_after(response))

        raise PublicHttpError(response.status_code)

    def _retry_delay(self, response: httpx.Response, attempt: int) -> float:
        retry_after = self._parse_retry_after(response)
        if retry_after is not None:
            return retry_after
        return self._backoff_delay(attempt)

    def _backoff_delay(self, attempt: int) -> float:
        return ldexp(self._retry_base_delay_seconds, attempt)

    def _parse_retry_after(self, response: httpx.Response) -> float | None:
        raw_value = response.headers.get("Retry-After")
        if not raw_value:
            return None

        try:
            numeric_delay: float = float(raw_value)
            return max(0.0, numeric_delay)
        except ValueError:
            pass

        try:
            retry_at = parsedate_to_datetime(raw_value)
        except (TypeError, ValueError, OverflowError):
            return None

        if retry_at.tzinfo is None:
            retry_at = retry_at.replace(tzinfo=UTC)

        delay_seconds: float = (retry_at.astimezone(UTC) - self._now()).total_seconds()

        return max(0.0, delay_seconds)

    @staticmethod
    def _is_retryable_status(status_code: int) -> bool:
        return status_code in {408, 429} or 500 <= status_code < 600

    def _build_headers(
        self,
        supplied_headers: Mapping[str, str] | None,
        bearer_token: str | None,
    ) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": self._USER_AGENT,
        }

        if supplied_headers is not None:
            headers.update(supplied_headers)

        if bearer_token is not None:
            headers["Authorization"] = f"Bearer {bearer_token}"

        return headers

    def _build_url(self, path: str) -> str:
        if not path.startswith("/") or path.startswith("//"):
            raise ValueError("Public API path must be an absolute relative path")
        return f"{self._base_url}{path}"

    def _now(self) -> datetime:
        return require_aware(self._clock()).astimezone(UTC)

    def _map_option_chain_contract(
        self,
        public_contract: PublicOptionChainContractPayload,
        *,
        underlying: str,
        expiration: date,
        right: OptionRight,
        received_timestamp: datetime,
    ) -> OptionContract:
        if public_contract.outcome != "SUCCESS":
            raise PublicResponseError(
                "Public option-chain response contained an unsuccessful contract"
            )

        symbol = public_contract.instrument.symbol
        osi_expiration, osi_right, osi_strike = self._parse_osi_symbol(symbol)
        if osi_expiration != expiration:
            raise PublicResponseError(
                "Public option-chain contract expiration did not match the request"
            )
        if osi_right != right:
            raise PublicResponseError(
                "Public option-chain contract right did not match its chain side"
            )
        if osi_strike != public_contract.option_details.strike_price:
            raise PublicResponseError(
                "Public option-chain contract strike did not match its option symbol"
            )

        source_timestamp = min(
            public_contract.bid_timestamp,
            public_contract.ask_timestamp,
        ).astimezone(UTC)

        try:
            public_greeks = public_contract.option_details.greeks
            greeks = None
            if public_greeks is not None:
                greeks = OptionGreeks(
                    delta=public_greeks.delta,
                    gamma=public_greeks.gamma,
                    theta=public_greeks.theta,
                    vega=public_greeks.vega,
                    rho=public_greeks.rho,
                    implied_volatility=public_greeks.implied_volatility,
                )

            return OptionContract(
                symbol=symbol,
                underlying=underlying,
                expiration=expiration,
                strike=public_contract.option_details.strike_price,
                right=right,
                quote=Quote(
                    symbol=symbol,
                    bid=public_contract.bid,
                    ask=public_contract.ask,
                    bid_size=public_contract.bid_size,
                    ask_size=public_contract.ask_size,
                    source_timestamp=source_timestamp,
                    received_timestamp=received_timestamp,
                ),
                volume=public_contract.volume,
                open_interest=public_contract.open_interest,
                greeks=greeks,
                tick_size=None,
            )
        except ValidationError as exc:
            raise PublicResponseError("Public option-chain response was unusable") from exc

    @staticmethod
    def _parse_osi_symbol(symbol: str) -> tuple[date, OptionRight, Decimal]:
        normalized = symbol.strip().upper()
        if len(normalized) <= 15 or not normalized[:-15]:
            raise PublicResponseError(
                "Public option-chain response contained an invalid option symbol"
            )

        expiration_code = normalized[-15:-9]
        right_code = normalized[-9]
        strike_code = normalized[-8:]
        if (
            not expiration_code.isdigit()
            or right_code not in {"C", "P"}
            or not strike_code.isdigit()
        ):
            raise PublicResponseError(
                "Public option-chain response contained an invalid option symbol"
            )

        try:
            expiration = date(
                2000 + int(expiration_code[:2]),
                int(expiration_code[2:4]),
                int(expiration_code[4:6]),
            )
        except ValueError as exc:
            raise PublicResponseError(
                "Public option-chain response contained an invalid option symbol"
            ) from exc

        right = OptionRight.CALL if right_code == "C" else OptionRight.PUT
        strike = Decimal(strike_code) / Decimal("1000")
        if strike <= 0:
            raise PublicResponseError(
                "Public option-chain response contained an invalid option symbol"
            )

        return expiration, right, strike

    @classmethod
    def _normalize_five_minute_timeframe(cls, value: str) -> str:
        normalized = value.strip().upper().replace("-", "_").replace(" ", "_")
        if normalized not in {"5M", "5MIN", "5_MINUTES", "FIVE_MINUTES"}:
            raise ValueError("Public bars currently support only the five-minute timeframe")
        return cls._FIVE_MINUTE_TIMEFRAME

    @staticmethod
    def _normalize_optional_bound(value: datetime | None, name: str) -> datetime | None:
        if value is None:
            return None
        try:
            return require_aware(value).astimezone(UTC)
        except ValueError as exc:
            raise ValueError(f"{name} must be timezone-aware") from exc

    @staticmethod
    def _read_required_secret(
        value: SecretStr | None,
        setting_name: str,
    ) -> str:
        if value is None:
            raise PublicConfigurationError(f"{setting_name} is required")

        raw_value = value.get_secret_value().strip()
        if not raw_value:
            raise PublicConfigurationError(f"{setting_name} is required")

        return raw_value

    @staticmethod
    def _validate_base_url(value: str) -> str:
        normalized = value.strip().rstrip("/")

        try:
            parsed = httpx.URL(normalized)
        except httpx.InvalidURL as exc:
            raise PublicConfigurationError("PUBLIC_API_BASE_URL is invalid") from exc

        if parsed.scheme != "https" or not parsed.host:
            raise PublicConfigurationError("PUBLIC_API_BASE_URL must be an HTTPS URL")

        return normalized
