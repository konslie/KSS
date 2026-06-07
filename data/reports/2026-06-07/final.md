# Morning Investment Briefing - 2026-06-07

## 1. Executive Summary

- **오늘의 한줄 요약:** **2026-06-07 브리핑은 해석보다 결측 확인이 중심**이다. `source.json`, `view_model.json`, `analysis_context.json` 기준으로 **가격, 기관/외인 수급, 뉴스, 공시가 모두 비어 있어** 포트폴리오별 방향성을 판정할 근거가 없다.
- **시장 위험도:** `view_model.json`상 표시는 **중립**이지만, **시장 지표 자체가 수집되지 않아 해석 신뢰도는 낮다**.
- **핵심 이벤트 3건:**
  1. **수집 범위 축소:** `yfinance`, `naver_finance`, `krx_open_api`, `krx_investor_flows`, `rss`, `naver_search_news`, `yfinance_news`, `dart`가 모두 `offline mode`로 기록됐다.
  2. **포트폴리오 15종목 결측:** `analysis_context.json`의 `missing_price_symbols`에 포트폴리오 **15개 전 종목**이 포함됐다.
  3. **뉴스·공시 부재:** `view_model.json`의 `coverage` 기준으로 **news_count 0**, **disclosure_count 0**, **seven_day_flow_available false**다.

## 2. 포트폴리오 영향도

| 종목 | 영향도 | 핵심 이슈 | 가격 | 기관 | 외인 | 7일 | 근거 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 현대차2우B | 중립 | 최근 종가 확인 필요 | 확인 필요 | 확인 필요 | 확인 필요 | 확인 필요 | `yfinance`·`naver_finance`·`krx_open_api`·`krx_investor_flows`·`dart`가 모두 `offline mode`로 기록돼 가격·수급·공시 확인이 불가했다. |
| 하나금융지주 | 중립 | 최근 종가 확인 필요 | 확인 필요 | 확인 필요 | 확인 필요 | 확인 필요 | `yfinance`·`naver_finance`·`krx_open_api`·`krx_investor_flows`·`dart`가 모두 `offline mode`로 기록돼 가격·수급·공시 확인이 불가했다. |
| 우리금융지주 | 중립 | 최근 종가 확인 필요 | 확인 필요 | 확인 필요 | 확인 필요 | 확인 필요 | `yfinance`·`naver_finance`·`krx_open_api`·`krx_investor_flows`·`dart`가 모두 `offline mode`로 기록돼 가격·수급·공시 확인이 불가했다. |
| 삼성전자 | 중립 | 최근 종가 확인 필요 | 확인 필요 | 확인 필요 | 확인 필요 | 확인 필요 | `yfinance`·`naver_finance`·`krx_open_api`·`krx_investor_flows`·`dart`가 모두 `offline mode`로 기록돼 가격·수급·공시 확인이 불가했다. |
| DB손해보험 | 중립 | 최근 종가 확인 필요 | 확인 필요 | 확인 필요 | 확인 필요 | 확인 필요 | `yfinance`·`naver_finance`·`krx_open_api`·`krx_investor_flows`·`dart`가 모두 `offline mode`로 기록돼 가격·수급·공시 확인이 불가했다. |
| 현대바이오 | 중립 | 최근 종가 확인 필요 | 확인 필요 | 확인 필요 | 확인 필요 | 확인 필요 | `yfinance`·`naver_finance`·`krx_open_api`·`krx_investor_flows`·`dart`가 모두 `offline mode`로 기록돼 가격·수급·공시 확인이 불가했다. |
| 금호석유화학 | 중립 | 최근 종가 확인 필요 | 확인 필요 | 확인 필요 | 확인 필요 | 확인 필요 | `yfinance`·`naver_finance`·`krx_open_api`·`krx_investor_flows`·`dart`가 모두 `offline mode`로 기록돼 가격·수급·공시 확인이 불가했다. |
| 이수페타시스 | 중립 | 최근 종가 확인 필요 | 확인 필요 | 확인 필요 | 확인 필요 | 확인 필요 | `yfinance`·`naver_finance`·`krx_open_api`·`krx_investor_flows`·`dart`가 모두 `offline mode`로 기록돼 가격·수급·공시 확인이 불가했다. |
| SCHD | 중립 | 최근 종가 확인 필요 | 확인 필요 |  |  | 확인 필요 | `yfinance`와 `yfinance_news`가 `offline mode`로 기록돼 최근 종가와 뉴스 확인이 불가했다. 미국 종목이라 국내 기관·외인 수급은 적용하지 않았다. |
| Apple | 중립 | 최근 종가 확인 필요 | 확인 필요 |  |  | 확인 필요 | `yfinance`와 `yfinance_news`가 `offline mode`로 기록돼 최근 종가와 뉴스 확인이 불가했다. 미국 종목이라 국내 기관·외인 수급은 적용하지 않았다. |
| Nvidia | 중립 | 최근 종가 확인 필요 | 확인 필요 |  |  | 확인 필요 | `yfinance`와 `yfinance_news`가 `offline mode`로 기록돼 최근 종가와 뉴스 확인이 불가했다. 미국 종목이라 국내 기관·외인 수급은 적용하지 않았다. |
| Coupang | 중립 | 최근 종가 확인 필요 | 확인 필요 |  |  | 확인 필요 | `yfinance`와 `yfinance_news`가 `offline mode`로 기록돼 최근 종가와 뉴스 확인이 불가했다. 미국 종목이라 국내 기관·외인 수급은 적용하지 않았다. |
| Rocket Lab | 중립 | 최근 종가 확인 필요 | 확인 필요 |  |  | 확인 필요 | `yfinance`와 `yfinance_news`가 `offline mode`로 기록돼 최근 종가와 뉴스 확인이 불가했다. 미국 종목이라 국내 기관·외인 수급은 적용하지 않았다. |
| Resolve AI | 중립 | 최근 종가 확인 필요 | 확인 필요 |  |  | 확인 필요 | `yfinance`와 `yfinance_news`가 `offline mode`로 기록돼 최근 종가와 뉴스 확인이 불가했다. 미국 종목이라 국내 기관·외인 수급은 적용하지 않았다. |
| Intuitive Machines | 중립 | 최근 종가 확인 필요 | 확인 필요 |  |  | 확인 필요 | `yfinance`와 `yfinance_news`가 `offline mode`로 기록돼 최근 종가와 뉴스 확인이 불가했다. 미국 종목이라 국내 기관·외인 수급은 적용하지 않았다. |

영향도 기준: 오늘 보고서의 **중립**은 우호/비우호 신호의 균형을 뜻하지 않는다. **판단 근거 자체가 비어 있어 보수적으로 중립 처리**한 값이다.

## 3. 금융주 브리핑

**하나금융지주**, **우리금융지주**, **DB손해보험**은 오늘 브리핑에서 금융주 강세나 약세를 해석할 근거가 없다. 가격이 없고, 기관·외인 수급도 없고, 관련 뉴스와 공시도 비어 있어 **뉴스·공시 이슈가 가격 흐름을 확인하는지, 수급이 그 방향을 뒷받침하는지**를 판단할 수 없다.

따라서 금융주 구간의 핵심은 방향성 해석이 아니라 **데이터 공백 자체를 리스크로 기록하는 것**이다. 다음 유효 실행에서는 최소한 **최근 종가**, **기관/외인 순매수·순매도**, **DART 공시 유무**가 함께 들어와야 금융주를 방어주로 볼지, 개별 이벤트 주도로 볼지 구분할 수 있다.

## 4. 현대차 / 환율

**현대차2우B**와 **USD/KRW** 모두 오늘 입력 파일에서는 확인할 수 없다. 그래서 환율이 자동차 우선주에 우호적인지 부담인지, 또는 가격과 외인 수급이 같은 방향으로 움직였는지 해석할 근거가 없다.

이 섹션에서 확인 가능한 사실은 하나뿐이다. `analysis_context.json`에서 **auto_fx 섹터 리스크가 `최근 종가 누락`으로만 기록**됐다는 점이다. 즉 오늘 브리핑에서는 환율 방향 자체보다 **환율-자동차 연결 해석이 불가능한 상태**라는 점을 먼저 받아들여야 한다.

## 5. 반도체 브리핑

**삼성전자**, **이수페타시스**, **Nvidia** 모두 `analysis_context.json`에서 **semiconductor 섹터**로 묶였지만, 실제 해석 단서는 비어 있다. 필라델피아반도체지수, 국내 반도체 가격, 외국인 수급, 관련 뉴스가 모두 누락돼 **AI 기대**, **외국인 매수/매도**, **가격 반응** 중 어느 것이 주된 변수였는지 말할 수 없다.

따라서 오늘 반도체 문단은 신호 해석이 아니라 **신호 부재 보고**에 가깝다. 특히 국내 반도체와 미국 대형주를 같은 서사로 묶으려면 최소한 가격 방향과 뉴스 출처가 필요하지만, 오늘 데이터셋에는 그 연결 고리가 없다.

## 6. 미국 포트폴리오 브리핑

**SCHD**, **Apple**, **Coupang**, **Rocket Lab**, **Resolve AI**, **Intuitive Machines**는 모두 **us_portfolio 섹터**로 묶였고, **Nvidia**는 반도체 섹터에 포함됐다. 그러나 공통적으로 `yfinance`와 `yfinance_news`가 `offline mode`라서 **최근 종가와 뉴스 이슈를 분리해서 읽는 작업 자체가 불가능**하다.

미국 종목은 원래 국내 기관·외인 수급이 직접 적용되지 않기 때문에, 평소에는 **뉴스 이슈와 가격 반응의 일치 여부**가 해석의 핵심이다. 오늘은 그 두 축이 모두 비어 있어, 미국 포트폴리오 섹션은 개별 종목 코멘트보다 **확인 보류 상태**를 명시하는 수준에 머문다.

## 7. 공시 및 뉴스

- **RSS 뉴스:** `news.md` 기준으로 **수집 항목 없음**.
- **Naver Search 뉴스:** `offline mode`로 스킵.
- **yfinance 뉴스:** `offline mode`로 스킵.
- **DART 공시:** `offline mode`로 스킵.

오늘 입력 파일에는 실제 기사 제목이나 공시명이 없으므로, 이 섹션에서도 **이슈 요약 대신 미수집 상태만 기록**한다.

## 8. 오늘의 관찰 포인트

1. **가격과 수급이 동시에 비면 영향도 해석은 사실상 불가능**하다.
2. **국내 종목 8개와 미국 종목 7개 모두 최근 종가 누락**으로 묶여, 포트폴리오 내 상대 강도를 비교할 수 없다.
3. `coverage.seven_day_flow_available`가 `false`라서 **당일 수급뿐 아니라 7거래일 누적 방향성도 판단할 수 없다**.
4. **뉴스 0건, 공시 0건**이라서 오늘 보고서는 이벤트 해석형 브리핑이 아니라 **데이터 공백 브리핑**에 가깝다.

## 9. 데이터 품질

- `make collect DATE=2026-06-07`는 네트워크 이름 해석 실패로 종료됐다. 이후 `make collect-offline DATE=2026-06-07`로 `source.json`과 `news.md`를 생성했다.
- `source.json`과 `view_model.json`에는 `yfinance`, `yfinance_indicators`, `naver_finance`, `krx_open_api`, `krx_investor_flows`, `rss`, `naver_search_news`, `yfinance_news`, `dart`가 모두 `offline mode`로 기록됐다.
- `analysis_context.json`의 `missing_price_symbols`에는 **005387, 086790, 316140, 005930, 005830, 048410, 011780, 007660, SCHD, AAPL, NVDA, CPNG, RKLB, RZLV, LUNR**가 포함됐다.
- `coverage` 기준으로 **뉴스 0건**, **공시 0건**, **7거래일 수급 없음**이다.
