from kss.models import CompanyType, PeerCandidate
from kss.peer_selection import market_cap_similarity, peer_multiple, select_peers


def test_market_cap_similarity_scores_target_range():
    assert market_cap_similarity(100, 80) == 1.0
    assert market_cap_similarity(100, 300) == 0.7
    assert market_cap_similarity(100, 500) == 0.3
    assert market_cap_similarity(None, 100) == 0.0


def test_select_peers_returns_top_three_comparable_candidates():
    candidates = [
        PeerCandidate(
            ticker="000001",
            company_name="Peer A",
            market="KOSPI",
            sector="반도체",
            company_type=CompanyType.NON_FINANCIAL,
            market_cap=90,
            per=10,
            pbr=1.1,
            roe_pct=11,
            industry_match_score=1.0,
        ),
        PeerCandidate(
            ticker="000002",
            company_name="Peer B",
            market="KOSPI",
            sector="반도체",
            company_type=CompanyType.NON_FINANCIAL,
            market_cap=130,
            per=12,
            pbr=1.2,
            roe_pct=10,
            industry_match_score=1.0,
        ),
        PeerCandidate(
            ticker="000003",
            company_name="Peer C",
            market="KOSDAQ",
            sector="반도체",
            company_type=CompanyType.NON_FINANCIAL,
            market_cap=250,
            per=14,
            pbr=1.3,
            roe_pct=8,
            industry_match_score=0.7,
        ),
        PeerCandidate(
            ticker="000004",
            company_name="Peer D",
            market="KOSPI",
            sector="바이오",
            company_type=CompanyType.NON_FINANCIAL,
            market_cap=900,
            per=20,
            pbr=3.0,
            roe_pct=1,
            industry_match_score=0.1,
        ),
        PeerCandidate(
            ticker="005930",
            company_name="Target",
            market="KOSPI",
            sector="반도체",
            company_type=CompanyType.NON_FINANCIAL,
            market_cap=100,
            per=9,
            pbr=1.0,
            roe_pct=10,
            industry_match_score=1.0,
        ),
    ]

    selected, confidence = select_peers(
        target_ticker="005930",
        target_company_type=CompanyType.NON_FINANCIAL,
        target_market="KOSPI",
        target_market_cap=100,
        target_roe_pct=10,
        candidates=candidates,
    )

    assert [peer.ticker for peer in selected] == ["000001", "000002", "000003"]
    assert confidence == "HIGH"


def test_peer_multiple_uses_median_for_three_and_average_for_two():
    assert peer_multiple([10, 30, 20]) == 20
    assert peer_multiple([10, 30]) == 20
    assert peer_multiple([None, -1, 15]) == 15

