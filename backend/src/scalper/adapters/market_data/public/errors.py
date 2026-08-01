class PublicApiError(RuntimeError):
    """Base exception for the Public market-data adapter."""


class PublicConfigurationError(PublicApiError):
    """Raised when required Public configuration is missing or invalid."""


class PublicAuthenticationError(PublicApiError):
    """Raised when Public rejects authentication."""


class PublicTransportError(PublicApiError):
    """Raised when a request cannot reach Public successfully."""


class PublicResponseError(PublicApiError):
    """Raised when Public returns an invalid or unexpected response."""


class PublicHttpError(PublicApiError):
    """Raised for an unsuccessful Public HTTP response."""

    def __init__(self, status_code: int) -> None:
        self.status_code = status_code
        super().__init__(f"Public API request failed with status {status_code}")


class PublicRateLimitError(PublicHttpError):
    """Raised when Public continues to rate-limit a request after retries."""

    def __init__(self, retry_after_seconds: float | None = None) -> None:
        self.retry_after_seconds = retry_after_seconds
        super().__init__(429)
