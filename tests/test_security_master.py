from kss.models import CompanyType
from kss.security_master import SAMPLE_LISTINGS, SecurityListing, SecurityType, identify_security


def _listings():
    return [
        SecurityListing(
            ticker="005930",
            company_name="삼성전자",
            market="KOSPI",
            sector="전기전자",
        ),
        SecurityListing(
            ticker="000810",
            company_name="삼성화재",
            market="KOSPI",
            sector="보험",
            financial_subtype="보험",
        ),
        SecurityListing(
            ticker="005935",
            company_name="삼성전자우",
            market="KOSPI",
            sector="전기전자",
            security_type=SecurityType.PREFERRED_STOCK,
        ),
        SecurityListing(
            ticker="123456",
            company_name="코넥스기업",
            market="KONEX",
            sector="제조",
        ),
    ]


def test_identify_security_matches_by_ticker_or_name():
    by_ticker = identify_security("5930", _listings())
    by_name = identify_security("삼성 전자", _listings())

    assert by_ticker is not None
    assert by_ticker.ticker == "005930"
    assert by_ticker.company_type == CompanyType.NON_FINANCIAL
    assert by_name == by_ticker


def test_identify_security_classifies_financial_company():
    result = identify_security("삼성화재", _listings())

    assert result is not None
    assert result.company_type == CompanyType.FINANCIAL
    assert result.is_supported is True


def test_identify_security_marks_excluded_instruments_as_unsupported():
    preferred = identify_security("삼성전자우", _listings())
    konex = identify_security("123456", _listings())

    assert preferred is not None
    assert preferred.is_supported is False
    assert konex is not None
    assert konex.is_supported is False


def test_identify_security_returns_none_for_unknown_query():
    assert identify_security("없는회사", _listings()) is None


def test_sample_listings_include_supported_and_excluded_examples():
    samsung = identify_security("005930", SAMPLE_LISTINGS)
    kodex = identify_security("KODEX200", SAMPLE_LISTINGS)

    assert samsung is not None
    assert samsung.is_supported is True
    assert kodex is not None
    assert kodex.is_supported is False
