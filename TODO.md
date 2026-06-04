# TODO

## Data Sources

- [ ] Add optional pykrx support.
  - Purpose: collect KRX-source reference data for Korean holdings and KRX indices.
  - Missing while skipped: Korean stock close/change/change_pct/volume/trading_value, plus KOSPI/KOSDAQ close/change/change_pct/volume/trading_value from KRX.
  - Current fallback: Korean stock prices come from Naver Finance; KOSPI/KOSDAQ come from yfinance market indicators.
  - Setup needed: confirm whether pykrx still requires `KRX_ID` and `KRX_PW`, then document required `.env` keys if needed.

## Reporting

- [ ] Hide implementation details from user-facing reports.
  - Do not expose `pykrx`, `KRX_ID`, `KRX_PW`, `fallback`, parser, cache, or API internals unless needed for debugging.
  - Prefer user-facing wording such as: "일부 KRX 보조 데이터는 수집되지 않았으며, 국내 종목 가격은 Naver Finance 기준으로 표시했다."

