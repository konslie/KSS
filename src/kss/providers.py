"""Data provider contracts and in-memory provider for KSS."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from kss.models import FinancialData, MarketData, PeerCandidate
from kss.security_master import SecurityListing


class DataProvider(Protocol):
    def listings(self) -> list[SecurityListing]:
        """Return securities available for identification."""

    def market_data(self, ticker: str) -> MarketData | None:
        """Return market data for a ticker."""

    def financial_data(self, ticker: str) -> FinancialData | None:
        """Return financial data for a ticker."""

    def peer_candidates(self, ticker: str) -> list[PeerCandidate]:
        """Return peer candidates for a ticker."""

    def historical_fair_values(self, ticker: str) -> list[float]:
        """Return historical fair-value estimates for a ticker."""

    def rim_fair_value(self, ticker: str) -> float | None:
        """Return RIM fair value for a ticker when available."""


@dataclass(frozen=True)
class InMemoryDataProvider:
    security_listings: list[SecurityListing]
    market_data_by_ticker: dict[str, MarketData] = field(default_factory=dict)
    financial_data_by_ticker: dict[str, FinancialData] = field(default_factory=dict)
    peer_candidates_by_ticker: dict[str, list[PeerCandidate]] = field(default_factory=dict)
    historical_fair_values_by_ticker: dict[str, list[float]] = field(default_factory=dict)
    rim_fair_values_by_ticker: dict[str, float] = field(default_factory=dict)

    def listings(self) -> list[SecurityListing]:
        return list(self.security_listings)

    def market_data(self, ticker: str) -> MarketData | None:
        return self.market_data_by_ticker.get(ticker)

    def financial_data(self, ticker: str) -> FinancialData | None:
        return self.financial_data_by_ticker.get(ticker)

    def peer_candidates(self, ticker: str) -> list[PeerCandidate]:
        return list(self.peer_candidates_by_ticker.get(ticker, []))

    def historical_fair_values(self, ticker: str) -> list[float]:
        return list(self.historical_fair_values_by_ticker.get(ticker, []))

    def rim_fair_value(self, ticker: str) -> float | None:
        return self.rim_fair_values_by_ticker.get(ticker)
