from collections.abc import Sequence
from datetime import date, datetime
from typing import Protocol

from scalper.domain.market import Bar, OptionChain, OptionExpiration, Quote


class MarketDataProvider(Protocol):
    async def get_bars(
        self,
        symbol: str,
        timeframe: str,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[Bar]: ...

    async def get_quote(self, symbol: str) -> Quote: ...

    async def get_option_expirations(self, symbol: str) -> Sequence[OptionExpiration]: ...

    async def get_option_chain(self, symbol: str, expiration: date) -> OptionChain: ...

    async def get_option_quotes(self, option_symbols: Sequence[str]) -> Sequence[Quote]: ...
