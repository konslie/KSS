from kss.models import CompanyMeta, CompanyType, FinancialData, MarketData, PeerCandidate, Verdict
from kss.valuation import evaluate_stock


def _company(company_type=CompanyType.NON_FINANCIAL):
    return CompanyMeta(
        ticker="005930",
        company_name="삼성전자",
        market="KOSPI",
        sector="전기전자",
        company_type=company_type,
    )


def _market(current_price=100, market_cap=1000):
    return MarketData(current_price=current_price, market_cap=market_cap)


def _financial(**overrides):
    data = {
        "eps": 10,
        "bps": 100,
        "roe_pct": 12,
        "roe_history_pct": (12, 11, 10),
        "operating_income_history": (120, 110, 100),
        "net_income_history": (100, 90, 80),
        "fcf_history": (20, 10, 5),
        "debt_ratio_history_pct": (80, 75, 70),
    }
    data.update(overrides)
    return FinancialData(**data)


def _peers():
    return [
        PeerCandidate(
            ticker="000001",
            company_name="Peer A",
            market="KOSPI",
            sector="전기전자",
            company_type=CompanyType.NON_FINANCIAL,
            market_cap=900,
            per=12,
            pbr=1.1,
            roe_pct=12,
            industry_match_score=1.0,
        ),
        PeerCandidate(
            ticker="000002",
            company_name="Peer B",
            market="KOSPI",
            sector="전기전자",
            company_type=CompanyType.NON_FINANCIAL,
            market_cap=1100,
            per=13,
            pbr=1.2,
            roe_pct=11,
            industry_match_score=1.0,
        ),
        PeerCandidate(
            ticker="000003",
            company_name="Peer C",
            market="KOSDAQ",
            sector="전기전자",
            company_type=CompanyType.NON_FINANCIAL,
            market_cap=1200,
            per=14,
            pbr=1.3,
            roe_pct=10,
            industry_match_score=0.9,
        ),
    ]


def test_evaluate_stock_returns_undervalued_when_base_upside_is_above_threshold():
    result = evaluate_stock(
        company=_company(),
        market_data=_market(current_price=100),
        financial_data=_financial(),
        peer_candidates=_peers(),
        historical_fair_values=[130, 140, 150],
    )

    assert result.verdict == Verdict.UNDERVALUED
    assert result.fair_value_band is not None
    assert result.fair_value_band.base > 120
    assert len(result.peer_group) == 3


def test_value_trap_risk_takes_priority_over_undervalued_verdict():
    result = evaluate_stock(
        company=_company(),
        market_data=_market(current_price=100),
        financial_data=_financial(
            roe_pct=4,
            roe_history_pct=(4, 8, 12),
            operating_income_history=(70, 90, 110),
            fcf_history=(-10, -20, 5),
        ),
        peer_candidates=_peers(),
        historical_fair_values=[130, 140, 150],
    )

    assert result.verdict == Verdict.VALUE_TRAP_RISK
    assert result.risk_flags.value_trap_risk is True
    assert result.confidence == "LOW"


def test_evaluate_stock_returns_overvalued_when_price_is_far_above_base_value():
    result = evaluate_stock(
        company=_company(),
        market_data=_market(current_price=200),
        financial_data=_financial(),
        peer_candidates=_peers(),
        historical_fair_values=[100, 110, 120],
    )

    assert result.verdict == Verdict.OVERVALUED


def test_unsupported_company_short_circuits():
    company = CompanyMeta(
        ticker="000000",
        company_name="Unsupported",
        market="KONEX",
        sector="",
        company_type=CompanyType.NON_FINANCIAL,
        is_supported=False,
    )

    result = evaluate_stock(
        company=company,
        market_data=_market(),
        financial_data=_financial(),
        peer_candidates=_peers(),
    )

    assert result.verdict == Verdict.UNSUPPORTED
    assert "unsupported_security" in result.data_warnings

