"""Peer selection logic."""

from __future__ import annotations

from statistics import mean, median

from kss.models import CompanyType, Confidence, PeerCandidate, SelectedPeer


def _bounded_score(value: float) -> float:
    return max(0.0, min(1.0, value))


def market_cap_similarity(target_market_cap: float | None, candidate_market_cap: float | None) -> float:
    if not target_market_cap or not candidate_market_cap or target_market_cap <= 0 or candidate_market_cap <= 0:
        return 0.0

    ratio = candidate_market_cap / target_market_cap
    if 0.5 <= ratio <= 2.0:
        return 1.0
    if 0.25 <= ratio <= 4.0:
        return 0.7
    return 0.3


def metric_availability(candidate: PeerCandidate) -> float:
    available = sum(value is not None for value in [candidate.per, candidate.pbr, candidate.roe_pct])
    return available / 3


def profitability_similarity(target_roe_pct: float | None, candidate_roe_pct: float | None) -> float:
    if target_roe_pct is None or candidate_roe_pct is None:
        return 0.0
    diff = abs(target_roe_pct - candidate_roe_pct)
    if diff <= 5:
        return 1.0
    if diff <= 10:
        return 0.7
    return 0.3


def exchange_similarity(target_market: str, candidate_market: str) -> float:
    return 1.0 if target_market == candidate_market else 0.5


def score_peer(
    *,
    target_company_type: CompanyType,
    target_market: str,
    target_market_cap: float | None,
    target_roe_pct: float | None,
    candidate: PeerCandidate,
) -> float:
    market_cap_score = market_cap_similarity(target_market_cap, candidate.market_cap)
    availability_score = metric_availability(candidate)
    profitability_score = profitability_similarity(target_roe_pct, candidate.roe_pct)
    liquidity_score = _bounded_score(candidate.liquidity_score)

    if target_company_type == CompanyType.FINANCIAL:
        return round(
            candidate.financial_subtype_match_score * 45
            + market_cap_score * 25
            + availability_score * 15
            + profitability_score * 10
            + liquidity_score * 5,
            2,
        )

    return round(
        candidate.industry_match_score * 40
        + market_cap_score * 25
        + availability_score * 15
        + profitability_score * 10
        + exchange_similarity(target_market, candidate.market) * 5
        + liquidity_score * 5,
        2,
    )


def select_peers(
    *,
    target_ticker: str,
    target_company_type: CompanyType,
    target_market: str,
    target_market_cap: float | None,
    target_roe_pct: float | None,
    candidates: list[PeerCandidate],
    limit: int = 3,
) -> tuple[list[SelectedPeer], Confidence | None]:
    eligible = [
        candidate
        for candidate in candidates
        if candidate.ticker != target_ticker
        and candidate.company_type == target_company_type
        and candidate.market_cap is not None
    ]

    scored = sorted(
        (
            (
                score_peer(
                    target_company_type=target_company_type,
                    target_market=target_market,
                    target_market_cap=target_market_cap,
                    target_roe_pct=target_roe_pct,
                    candidate=candidate,
                ),
                candidate,
            )
            for candidate in eligible
        ),
        key=lambda item: item[0],
        reverse=True,
    )

    selected = [
        SelectedPeer(
            ticker=candidate.ticker,
            company_name=candidate.company_name,
            reason=_peer_reason(target_company_type, candidate),
            peer_score=score,
            per=candidate.per,
            pbr=candidate.pbr,
        )
        for score, candidate in scored[:limit]
    ]

    if len(selected) >= 3:
        confidence = Confidence.HIGH
    elif len(selected) == 2:
        confidence = Confidence.MEDIUM
    elif len(selected) == 1:
        confidence = Confidence.LOW
    else:
        confidence = None

    return selected, confidence


def peer_multiple(values: list[float | None]) -> float | None:
    valid = [value for value in values if value is not None and value > 0]
    if not valid:
        return None
    if len(valid) == 1:
        return valid[0]
    if len(valid) == 2:
        return mean(valid)
    return median(valid)


def _peer_reason(company_type: CompanyType, candidate: PeerCandidate) -> str:
    if company_type == CompanyType.FINANCIAL:
        if candidate.subtype:
            return f"동일 또는 유사 금융 subtype: {candidate.subtype}"
        return "금융주 비교 후보"
    return "동일 또는 유사 산업 비교 후보"

