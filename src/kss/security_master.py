"""Security identification for KRX-listed instruments."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from kss.models import CompanyMeta, CompanyType


class SecurityType(str, Enum):
    COMMON_STOCK = "COMMON_STOCK"
    PREFERRED_STOCK = "PREFERRED_STOCK"
    ETF = "ETF"
    ETN = "ETN"
    REIT = "REIT"
    SPAC = "SPAC"
    OTHER = "OTHER"


SUPPORTED_MARKETS = {"KOSPI", "KOSDAQ"}
FINANCIAL_SECTORS = {"은행", "보험", "증권", "카드", "캐피탈", "금융지주"}


@dataclass(frozen=True)
class SecurityListing:
    ticker: str
    company_name: str
    market: str
    sector: str
    security_type: SecurityType = SecurityType.COMMON_STOCK
    financial_subtype: str | None = None


def identify_security(query: str, listings: list[SecurityListing]) -> CompanyMeta | None:
    normalized_query = _normalize_query(query)
    if not normalized_query:
        return None

    for listing in listings:
        if normalized_query in {_normalize_ticker(listing.ticker), _normalize_name(listing.company_name)}:
            return _to_company_meta(listing)

    return None


def _to_company_meta(listing: SecurityListing) -> CompanyMeta:
    is_supported = listing.market in SUPPORTED_MARKETS and listing.security_type == SecurityType.COMMON_STOCK
    return CompanyMeta(
        ticker=_normalize_ticker(listing.ticker),
        company_name=listing.company_name,
        market=listing.market,
        sector=listing.sector,
        company_type=_company_type(listing),
        is_supported=is_supported,
    )


def _company_type(listing: SecurityListing) -> CompanyType:
    if listing.financial_subtype in FINANCIAL_SECTORS or listing.sector in FINANCIAL_SECTORS:
        return CompanyType.FINANCIAL
    return CompanyType.NON_FINANCIAL


def _normalize_query(query: str) -> str:
    stripped = query.strip()
    if stripped.isdigit():
        return _normalize_ticker(stripped)
    return _normalize_name(stripped)


def _normalize_ticker(ticker: str) -> str:
    return ticker.strip().zfill(6)


def _normalize_name(name: str) -> str:
    return "".join(name.split()).casefold()
