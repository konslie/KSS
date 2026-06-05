# TODO

## Data Sources

- [ ] Revisit whether KRX Open API should remain.
  - Current primary practical path: pykrx with `KRX_ID` and `KRX_PW`.
  - KRX Open API is not urgent while pykrx covers Korean holdings, KOSPI/KOSDAQ indices, and 개인/기관/외국인 investor flow.
  - Later decision: remove KRX Open API code/env if it keeps adding complexity without better reliability.

## Reporting

- [ ] Hide implementation details from user-facing reports.
  - Do not expose `KRX_AUTH_KEY`, fallback, parser, cache, or API internals unless needed for debugging.
  - Prefer user-facing wording such as: "일부 KRX 보조 데이터는 수집되지 않았으며, 국내 종목 가격은 Naver Finance 기준으로 표시했다."

## Frontend

- [ ] Consider richer portfolio row interactions after the static dashboard stabilizes.
  - Candidate additions: source filtering, row expand/collapse for full news/disclosure text, table sorting.
  - Keep GitHub Pages static delivery and embedded JSON support.
- [ ] Keep market indicator sparklines as line-only SVGs.
  - Do not use filled area shapes in main indicator cards unless the design is explicitly revised.
