"""Pure valuation logic for KSS."""

from __future__ import annotations

from statistics import median

from kss.models import (
    CompanyMeta,
    CompanyType,
    Confidence,
    FairValueBand,
    FinancialData,
    MarketData,
    ModelResult,
    PeerCandidate,
    RiskFlags,
    ValuationResult,
    Verdict,
)
from kss.peer_selection import peer_multiple, select_peers

FINANCIAL_WEIGHTS = {
    "rim": 0.50,
    "peer_pbr": 0.25,
    "historical_pbr": 0.20,
    "dividend_yield": 0.05,
}

NON_FINANCIAL_WEIGHTS = {
    "peer_per": 0.40,
    "peer_pbr": 0.20,
    "historical_multiple": 0.40,
}


def evaluate_stock(
    *,
    company: CompanyMeta,
    market_data: MarketData | None,
    financial_data: FinancialData | None,
    peer_candidates: list[PeerCandidate],
    historical_fair_values: list[float] | None = None,
    rim_fair_value: float | None = None,
    data_warnings: list[str] | None = None,
) -> ValuationResult:
    warnings = list(data_warnings or [])

    if not company.is_supported:
        return ValuationResult(
            ticker=company.ticker,
            company_name=company.company_name,
            market=company.market,
            sector=company.sector,
            company_type=company.company_type,
            current_price=market_data.current_price if market_data else None,
            verdict=Verdict.UNSUPPORTED,
            confidence=Confidence.LOW,
            fair_value_band=None,
            model_results={},
            data_warnings=warnings + ["unsupported_security"],
        )

    if not market_data or market_data.current_price <= 0 or not financial_data:
        return ValuationResult(
            ticker=company.ticker,
            company_name=company.company_name,
            market=company.market,
            sector=company.sector,
            company_type=company.company_type,
            current_price=market_data.current_price if market_data else None,
            verdict=Verdict.INSUFFICIENT_DATA,
            confidence=Confidence.LOW,
            fair_value_band=None,
            model_results={},
            data_warnings=warnings + ["missing_core_data"],
        )

    selected_peers, peer_confidence = select_peers(
        target_ticker=company.ticker,
        target_company_type=company.company_type,
        target_market=company.market,
        target_market_cap=market_data.market_cap,
        target_roe_pct=financial_data.roe_pct,
        candidates=peer_candidates,
    )

    risk_flags = detect_risk_flags(financial_data, peer_count=len(selected_peers))
    model_results = build_model_results(
        company_type=company.company_type,
        financial_data=financial_data,
        selected_peer_pers=[peer.per for peer in selected_peers],
        selected_peer_pbrs=[peer.pbr for peer in selected_peers],
        historical_fair_values=historical_fair_values or [],
        rim_fair_value=rim_fair_value,
        peer_confidence=peer_confidence,
    )
    fair_value_band = combine_model_results(model_results)

    if fair_value_band is None:
        verdict = Verdict.INSUFFICIENT_DATA
        confidence = Confidence.LOW
        warnings.append("no_valid_valuation_model")
    else:
        verdict = determine_verdict(market_data.current_price, fair_value_band, risk_flags)
        confidence = determine_confidence(
            model_results=model_results,
            peer_count=len(selected_peers),
            risk_flags=risk_flags,
            data_warnings=warnings,
        )

    return ValuationResult(
        ticker=company.ticker,
        company_name=company.company_name,
        market=company.market,
        sector=company.sector,
        company_type=company.company_type,
        current_price=market_data.current_price,
        verdict=verdict,
        confidence=confidence,
        fair_value_band=fair_value_band,
        model_results=model_results,
        peer_group=selected_peers,
        risk_flags=risk_flags,
        explanation=build_explanation(market_data.current_price, fair_value_band, verdict),
        data_warnings=warnings,
    )


def build_model_results(
    *,
    company_type: CompanyType,
    financial_data: FinancialData,
    selected_peer_pers: list[float | None],
    selected_peer_pbrs: list[float | None],
    historical_fair_values: list[float],
    rim_fair_value: float | None,
    peer_confidence: Confidence | None,
) -> dict[str, ModelResult]:
    if company_type == CompanyType.FINANCIAL:
        model_results = {
            "rim": ModelResult(rim_fair_value, FINANCIAL_WEIGHTS["rim"], _confidence_for_value(rim_fair_value)),
            "peer_pbr": ModelResult(
                _pbr_fair_value(financial_data.bps, selected_peer_pbrs),
                FINANCIAL_WEIGHTS["peer_pbr"],
                peer_confidence or Confidence.LOW,
            ),
            "historical_pbr": ModelResult(
                _historical_fair_value(historical_fair_values),
                FINANCIAL_WEIGHTS["historical_pbr"],
                _confidence_for_values(historical_fair_values),
            ),
        }
        return {name: result for name, result in model_results.items() if result.fair_value is not None}

    model_results = {
        "peer_per": ModelResult(
            _per_fair_value(financial_data.eps, selected_peer_pers),
            NON_FINANCIAL_WEIGHTS["peer_per"],
            peer_confidence or Confidence.LOW,
        ),
        "peer_pbr": ModelResult(
            _pbr_fair_value(financial_data.bps, selected_peer_pbrs),
            NON_FINANCIAL_WEIGHTS["peer_pbr"],
            peer_confidence or Confidence.LOW,
        ),
        "historical_multiple": ModelResult(
            _historical_fair_value(historical_fair_values),
            NON_FINANCIAL_WEIGHTS["historical_multiple"],
            _confidence_for_values(historical_fair_values),
        ),
    }
    return {name: result for name, result in model_results.items() if result.fair_value is not None}


def combine_model_results(model_results: dict[str, ModelResult]) -> FairValueBand | None:
    usable = [result for result in model_results.values() if result.fair_value is not None and result.weight > 0]
    if not usable:
        return None

    total_weight = sum(result.weight for result in usable)
    base = sum(float(result.fair_value) * result.weight for result in usable) / total_weight
    values = sorted(float(result.fair_value) for result in usable)

    low_anchor = values[0]
    high_anchor = values[-1]
    low = min(low_anchor, base * 0.9)
    high = max(high_anchor, base * 1.1)

    return FairValueBand(low=round(low, 2), base=round(base, 2), high=round(high, 2))


def determine_verdict(current_price: float, fair_value_band: FairValueBand, risk_flags: RiskFlags) -> Verdict:
    upside_pct = (fair_value_band.base - current_price) / current_price * 100

    if upside_pct >= 20 and risk_flags.value_trap_risk:
        return Verdict.VALUE_TRAP_RISK
    if upside_pct >= 20:
        return Verdict.UNDERVALUED
    if upside_pct <= -15:
        return Verdict.OVERVALUED
    return Verdict.FAIRLY_VALUED


def determine_confidence(
    *,
    model_results: dict[str, ModelResult],
    peer_count: int,
    risk_flags: RiskFlags,
    data_warnings: list[str],
) -> Confidence:
    if risk_flags.value_trap_risk or peer_count <= 1 or len(model_results) <= 1:
        return Confidence.LOW
    if data_warnings or peer_count == 2 or _model_spread_is_wide(model_results):
        return Confidence.MEDIUM
    return Confidence.HIGH


def detect_risk_flags(financial_data: FinancialData, *, peer_count: int) -> RiskFlags:
    roe_declining = _strictly_declining(financial_data.roe_history_pct[:3])
    earnings_declining = _strictly_declining(financial_data.operating_income_history[:3]) or _strictly_declining(
        financial_data.net_income_history[:3]
    )
    fcf_negative = len(financial_data.fcf_history[:2]) == 2 and all(value < 0 for value in financial_data.fcf_history[:2])
    high_leverage = _leverage_spiked(financial_data.debt_ratio_history_pct[:3])

    low_roe = financial_data.roe_pct is not None and financial_data.roe_pct < 6
    value_trap_signals = sum([roe_declining, earnings_declining, fcf_negative, high_leverage, low_roe])

    return RiskFlags(
        value_trap_risk=value_trap_signals >= 2,
        roe_declining=roe_declining,
        earnings_declining=earnings_declining,
        fcf_negative=fcf_negative,
        high_leverage=high_leverage,
        insufficient_peer_count=peer_count < 3,
    )


def build_explanation(current_price: float, fair_value_band: FairValueBand | None, verdict: Verdict) -> list[str]:
    if fair_value_band is None:
        return ["핵심 데이터 부족으로 적정가 밴드를 산출하지 못함"]

    upside_pct = (fair_value_band.base - current_price) / current_price * 100
    return [
        f"현재 주가는 기준 적정가 대비 {upside_pct:.1f}% 차이가 있음",
        f"최종 판정은 {verdict.value}",
    ]


def _per_fair_value(eps: float | None, peer_pers: list[float | None]) -> float | None:
    multiple = peer_multiple([value for value in peer_pers if value is not None and 0 < value <= 100])
    if eps is None or eps <= 0 or multiple is None:
        return None
    return round(eps * multiple, 2)


def _pbr_fair_value(bps: float | None, peer_pbrs: list[float | None]) -> float | None:
    multiple = peer_multiple(peer_pbrs)
    if bps is None or bps <= 0 or multiple is None:
        return None
    return round(bps * multiple, 2)


def _historical_fair_value(values: list[float]) -> float | None:
    valid = [value for value in values if value > 0]
    if not valid:
        return None
    return round(median(valid), 2)


def _confidence_for_value(value: float | None) -> Confidence:
    return Confidence.MEDIUM if value is not None else Confidence.LOW


def _confidence_for_values(values: list[float]) -> Confidence:
    if len([value for value in values if value > 0]) >= 3:
        return Confidence.HIGH
    if values:
        return Confidence.MEDIUM
    return Confidence.LOW


def _strictly_declining(values: tuple[float, ...]) -> bool:
    if len(values) < 3:
        return False
    return values[0] < values[1] < values[2]


def _leverage_spiked(values: tuple[float, ...]) -> bool:
    if len(values) < 2:
        return False
    return values[0] - values[-1] >= 30


def _model_spread_is_wide(model_results: dict[str, ModelResult]) -> bool:
    values = [float(result.fair_value) for result in model_results.values() if result.fair_value is not None]
    if len(values) < 2:
        return False
    low, high = min(values), max(values)
    return high / low >= 1.6 if low > 0 else True

