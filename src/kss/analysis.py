"""Application-level stock analysis orchestration."""

from __future__ import annotations

from kss.models import CompanyMeta, CompanyType, ValuationResult
from kss.providers import DataProvider
from kss.security_master import identify_security
from kss.valuation import evaluate_stock


def analyze_stock(query: str, provider: DataProvider) -> ValuationResult:
    company = identify_security(query, provider.listings())
    if company is None:
        company = CompanyMeta(
            ticker="",
            company_name=query,
            market="",
            sector="",
            company_type=CompanyType.NON_FINANCIAL,
            is_supported=False,
        )
        return evaluate_stock(
            company=company,
            market_data=None,
            financial_data=None,
            peer_candidates=[],
            data_warnings=["unknown_security"],
        )

    return evaluate_stock(
        company=company,
        market_data=provider.market_data(company.ticker),
        financial_data=provider.financial_data(company.ticker),
        peer_candidates=provider.peer_candidates(company.ticker),
        historical_fair_values=provider.historical_fair_values(company.ticker),
        rim_fair_value=provider.rim_fair_value(company.ticker),
    )


def result_to_dict(result: ValuationResult) -> dict[str, object]:
    fair_value_band = None
    if result.fair_value_band is not None:
        fair_value_band = {
            "low": result.fair_value_band.low,
            "base": result.fair_value_band.base,
            "high": result.fair_value_band.high,
        }

    return {
        "ticker": result.ticker,
        "company_name": result.company_name,
        "market": result.market,
        "sector": result.sector,
        "company_type": result.company_type.value,
        "current_price": result.current_price,
        "verdict": result.verdict.value,
        "confidence": result.confidence.value,
        "fair_value_band": fair_value_band,
        "models": {
            name: {
                "fair_value": model_result.fair_value,
                "weight": model_result.weight,
                "confidence": model_result.confidence.value,
            }
            for name, model_result in result.model_results.items()
        },
        "peers": [
            {
                "ticker": peer.ticker,
                "company_name": peer.company_name,
                "peer_score": peer.peer_score,
                "reason": peer.reason,
            }
            for peer in result.peer_group
        ],
        "risk_flags": {
            "value_trap_risk": result.risk_flags.value_trap_risk,
            "roe_declining": result.risk_flags.roe_declining,
            "earnings_declining": result.risk_flags.earnings_declining,
            "fcf_negative": result.risk_flags.fcf_negative,
            "high_leverage": result.risk_flags.high_leverage,
            "insufficient_peer_count": result.risk_flags.insufficient_peer_count,
        },
        "explanation": list(result.explanation),
        "data_warnings": list(result.data_warnings),
    }
