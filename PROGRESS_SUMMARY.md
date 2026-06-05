# KSS 진행 요약

마지막 업데이트: 2026-06-06

## 현재 목표

KSS는 개인 포트폴리오 기준의 아침 투자 브리핑을 생성한다.

- Python 수집기는 시장 지표, 보유 종목 가격, 투자자별 수급, 뉴스, 공시를 모은다.
- Codex는 수집된 원천 데이터와 화면용 구조 데이터를 바탕으로 최종 리포트 문장을 작성한다.
- 정적 프론트엔드는 `docs/` 아래 GitHub Pages용 HTML로 배포된다.

## 데이터 흐름

현재 파이프라인은 아래 순서다.

1. `src/collect.py`
   - `data/incoming/YYYY-MM-DD/source.json` 생성
   - `data/incoming/YYYY-MM-DD/news.md` 생성
   - yfinance, Naver Finance, Naver Search, CNBC RSS, DART, KRX/pykrx 기반 데이터를 수집

2. `src/build_view_model.py`
   - `data/reports/YYYY-MM-DD/view_model.json` 생성
   - 프론트엔드가 바로 사용할 수 있는 가격, 7거래일 종가, 수급, 뉴스, 공시, 영향도, 핵심 이슈를 구성

3. `src/build_analysis_context.py`
   - `data/reports/YYYY-MM-DD/analysis_context.json` 생성
   - Codex가 최종 리포트 문장을 쓸 때 사용할 압축된 분석 컨텍스트를 구성

4. Codex 리포트 작성
   - `data/reports/YYYY-MM-DD/final.md` 생성
   - 투자 추천, 목표가, 확정 전망은 금지
   - `source.json`, `news.md`, `view_model.json`에 없는 사실은 추가하지 않음

5. `src/render_html.py`
   - `docs/index.html`
   - `docs/reports/YYYY-MM-DD.html`
   - `docs/reports/YYYY-MM-DD.json`
   - `docs/assets/report.css`
   - `docs/assets/report.js`

## 주요 변경 사항

### 데이터 수집

- yfinance 가격 수집에서 `Close = NaN`인 일봉 행을 제거한 뒤 최신/직전/최근 7거래일 종가를 계산하도록 수정했다.
- yfinance 수집 결과에 `as_of_date`, `recent_dates`를 추가했다.
- CPNG, RKLB, RZLV, LUNR처럼 마지막 행이 `NaN`으로 들어오던 종목도 실제 유효한 최신 종가가 반영된다.
- KRX Open API 기반 수급 수집 설정을 추가했고, API 경로가 없거나 인증 실패하면 pykrx fallback을 사용하도록 구성했다.
- 국내 종목은 개인/기관/외국인 최신 순매수와 7거래일 합계를 화면용 데이터에 포함한다.
- 미국 종목 수급은 현재 공란 또는 `국내 종목만` 상태로 둔다.

### 데이터 구조

- 원천 데이터와 화면 데이터를 분리했다.
- `source.json`은 가능한 한 풍부한 원천 데이터를 유지한다.
- `view_model.json`은 프론트엔드 렌더링에 필요한 구조화 데이터를 담당한다.
- `analysis_context.json`은 리포트 문장 생성을 위한 컨텍스트를 담당한다.
- `DATA_SCHEMA.md`에 주요 산출물 구조를 정리했다.

### 프론트엔드

- Python이 인라인 HTML을 직접 찍어내는 방식에서 벗어나, `docs/assets/report.css`와 `docs/assets/report.js` 기반의 정적 프론트엔드 구조로 이동했다.
- 다크모드 기반의 증권사 리포트 스타일로 재설계했다.
- 히어로 문구는 `개인 포트폴리오 관련 브리핑`으로 변경했다.
- 메인 제목은 `KO_데일리브리핑(yy.mmdd)` 형식으로 변경했다.
- 상단 archive 영역의 sticky 동작을 제거했다.
- 주요 지표 카드는 세련된 라인 스파크라인을 사용한다.
- 포트폴리오 테이블은 가격, 등락, 7일 추이, 수급, 영향, 핵심 이슈, 한줄 요약 중심으로 재구성했다.
- `뉴스 n / 공시 m` 카운트는 제거하고 뉴스/공시 제목 기반 한줄 요약으로 대체했다.
- 뉴스 소스 뱃지는 포트폴리오 영역에서만 사용한다.

### 리포트 규칙

- Executive Summary와 섹터별 브리핑의 주요 키워드는 볼드 처리한다.
- Executive Summary에서는 뱃지를 쓰지 않고 실제 출처명을 유지한다.
- 포트폴리오 영향도 하단에는 긍정/중립/부정 기준을 표시한다.
- 주요 거시지표는 수집 기준일과 마감 지표 기준을 명시한다.

## 현재 검증 상태

최근 검증 명령:

```bash
make test
```

결과:

- 27개 테스트 통과
- `docs/index.html` 및 `docs/reports/2026-06-05.html` 재생성 완료

## 남은 과제

- 실제 자동화에서 `collect -> view-model -> analysis-context -> Codex final.md -> render-html` 순서를 안정적으로 연결해야 한다.
- KRX Open API의 실제 수급 API 경로가 확정되면 `.env`와 수집 로직을 다시 맞춰야 한다.
- 현재 프론트엔드는 정적 JS/CSS 기반이다. 필요하면 이후 React/Vite 등 별도 앱 구조로 확장할 수 있다.
- `final.md` 문장에는 과거 수집 실패 설명이 남아 있을 수 있으므로, 최신 `analysis_context.json` 기준으로 Codex 리포트 본문을 다시 작성하는 단계가 필요하다.
