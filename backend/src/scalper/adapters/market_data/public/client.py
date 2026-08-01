import asyncio
from collections.abc import Awaitable, Callable, Mapping
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from math import ldexp
from types import TracebackType
from typing import Any, Self

import httpx
from pydantic import SecretStr, ValidationError

from scalper.core.config import Settings
from scalper.core.time import require_aware, utc_now

from .errors import (
    PublicAuthenticationError,
    PublicConfigurationError,
    PublicHttpError,
    PublicRateLimitError,
    PublicResponseError,
    PublicTransportError,
)
from .models import PublicAccessTokenResponse

Clock = Callable[[], datetime]
Sleeper = Callable[[float], Awaitable[None]]


class PublicMarketDataClient:
    """Authenticated HTTP client restricted to Public market-data requests."""

    _AUTH_PATH = "/userapiauthservice/personal/access-tokens"
    _USER_AGENT = "options-intraday-scalper/0.1.0"

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
