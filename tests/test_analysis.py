from kss.analysis import analyze_stock, result_to_dict
from kss.mock_data import MOCK_PROVIDER
from kss.models import Verdict


def test_analyze_stock_runs_full_flow_for_supported_stock():
    result = analyze_stock("삼성전자", MOCK_PROVIDER)

    assert result.ticker == "005930"
    assert result.current_price == 71000
    assert result.verdict in {Verdict.UNDERVALUED, Verdict.FAIRLY_VALUED, Verdict.OVERVALUED}
    assert result.fair_value_band is not None
    assert result.model_results
    assert result.peer_group


def test_analyze_stock_returns_unsupported_for_excluded_security():
    result = analyze_stock("KODEX200", MOCK_PROVIDER)

    assert result.verdict == Verdict.UNSUPPORTED
    assert "unsupported_security" in result.data_warnings


def test_analyze_stock_returns_unknown_security_warning():
    result = analyze_stock("없는회사", MOCK_PROVIDER)

    assert result.verdict == Verdict.UNSUPPORTED
    assert "unknown_security" in result.data_warnings
    assert "unsupported_security" in result.data_warnings


def test_result_to_dict_serializes_public_result_shape():
    result = analyze_stock("KB금융", MOCK_PROVIDER)
    payload = result_to_dict(result)

    assert payload["ticker"] == "105560"
    assert payload["company_type"] == "FINANCIAL"
    assert payload["fair_value_band"] is not None
    assert "rim" in payload["models"]
    assert isinstance(payload["peers"], list)
