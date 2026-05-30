"""Domain models for KSS valuation."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class CompanyType(str, Enum):
    FINANCIAL = "FINANCIAL"
    NON_FINANCIAL = "NON_FINANCIAL"


class Verdict(str, Enum):
    UNDERVALUED = "UNDERVALUED"
    FAIRLY_VALUED = "FAIRLY_VALUED"
    OVERVALUED = "OVERVALUED"
    VALUE_TRAP_RISK = "VALUE_TRAP_RISK"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    UNSUPPORTED = "UNSUPPORTED"


class Confidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass(frozen=True)
class CompanyMeta:
    ticker: str
    company_name: str
    market: str
    sector: str
    company_type: CompanyType
    is_supported: bool = True


@dataclass(frozen=True)
class MarketData:
    current_price: float
    market_cap: float | None = None
    shares_outstanding: float | None = None
    high_52w: float | None = None
    low_52w: float | None = None


@dataclass(frozen=True)
class FinancialData:
    eps: float | None = None
    bps: float | None = None
    roe_pct: float | None = None
    roe_3yr_avg_pct: float | None = None
    roe_history_pct: tuple[float, ...] = ()
    operating_income_history: tuple[float, ...] = ()
    net_income_history: tuple[float, ...] = ()
    fcf_history: tuple[float, ...] = ()
    debt_ratio_history_pct: tuple[float, ...] = ()
    dps: float | None = None


@dataclass(frozen=True)
class PeerCandidate:
    ticker: str
    company_name: str
    market: str
    sector: str
    company_type: CompanyType
    market_cap: float | None
    per: float | None = None
    pbr: float | None = None
    roe_pct: float | None = None
    liquidity_score: float = 1.0
    subtype: str | None = None
    industry_match_score: float = 0.0
    financial_subtype_match_score: float = 0.0


@dataclass(frozen=True)
class SelectedPeer:
    ticker: str
    company_name: str
    reason: str
    peer_score: float
    per: float | None = None
    pbr: float | None = None


@dataclass(frozen=True)
class FairValueBand:
    low: float
    base: float
    high: float


@dataclass(frozen=True)
class ModelResult:
    fair_value: float | None
    weight: float
    confidence: Confidence


@dataclass(frozen=True)
class RiskFlags:
    value_trap_risk: bool = False
    roe_declining: bool = False
    earnings_declining: bool = False
    fcf_negative: bool = False
    high_leverage: bool = False
    insufficient_peer_count: bool = False


@dataclass(frozen=True)
class ValuationResult:
    ticker: str
    company_name: str
    market: str
    sector: str
    company_type: CompanyType
    current_price: float | None
    verdict: Verdict
    confidence: Confidence
    fair_value_band: FairValueBand | None
    model_results: dict[str, ModelResult]
    peer_group: list[SelectedPeer] = field(default_factory=list)
    risk_flags: RiskFlags = field(default_factory=RiskFlags)
    explanation: list[str] = field(default_factory=list)
    data_warnings: list[str] = field(default_factory=list)
