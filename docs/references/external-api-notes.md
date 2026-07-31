# External API Notes Reviewed for Phase 0

Reviewed: 2026-07-29

## Public API

Official documentation currently provides:

- Personal access-token exchange from a generated secret key.
- Real-time quotes for equities and options.
- Option-expiration lookup.
- Option-chain retrieval by actual listed expiration.
- Historical bars with aggregation.
- Option Greeks.

The application will use only these market-data functions. Although Public also exposes trading functions, Public execution and account state are outside the approved Version 1 boundary.

The Public Individual API documentation states that individual access is for personal, non-commercial use. A commercial or multi-user deployment would require a separate terms and licensing review.

Official references:

- https://public.com/api/docs
- https://public.com/api/docs/quickstart
- https://public.com/api/docs/resources/market-data/get-quotes
- https://public.com/api/docs/resources/market-data/get-option-expirations
- https://public.com/api/docs/resources/market-data/get-option-chain
- https://public.com/api/docs/resources/market-data/get-bars-v2-with-aggregation

## Webull OpenAPI

Webull currently requires an API application before credentials can be used. Its documentation says review is typically 1–2 business days at the earliest, and its sandbox and production environments are isolated. This timing is not guaranteed and does not alter the project sequence: Webull implementation remains after Phase 4.

Official references:

- https://developer.webull.com/apis/docs/getting-started/
- https://developer.webull.com/apis/docs/authentication/IndividualApplicationAPI/
- https://developer.webull.com/apis/docs/about-open-api/
