# KSS Report Frontend Redesign

## Goal

리포트 페이지는 `docs/` 정적 배포 방식을 유지하되, 화면 구성은 CSS와 JavaScript 중심의 프론트엔드로 관리한다.

Python은 수집, 구조화, HTML shell 생성에 집중한다. 프론트엔드는 embedded JSON을 읽어 전문 증권사 리포트에 가까운 히어로, 지표 카드, 포트폴리오 테이블, 출처 뱃지, 스파크라인을 렌더링한다.

## Structure

```text
docs/
  assets/
    report.css
    report.js
  index.html
  reports/
    YYYY-MM-DD.html
    YYYY-MM-DD.json

src/
  build_view_model.py
  render_html.py
```

## Responsibilities

### Python Collector

- `data/incoming/YYYY-MM-DD/source.json` and `news.md`를 생성한다.
- 한 소스가 실패해도 전체 수집이 중단되지 않도록 실패 상태를 기록한다.

### View Model

- `data/reports/YYYY-MM-DD/view_model.json`이 프론트엔드의 주요 정량 데이터 원천이다.
- 시장 지표는 최근 종가, 직전 거래일 종가, 7거래일 종가 배열, 등락폭, 등락률을 보존한다.
- 포트폴리오는 종목별 최근 가격, 7거래일 가격 추이, 최신 투자자별 수급, 7거래일 수급 합계, 뉴스/공시 원천을 보존한다.

### Python Renderer

- `final.md`를 report JSON으로 변환한다.
- `view_model.json`과 report JSON을 page JSON으로 묶는다.
- `docs/index.html`, `docs/reports/YYYY-MM-DD.html`, `docs/reports/YYYY-MM-DD.json`을 생성한다.
- CSS/JS 기본 문자열은 `docs/assets/`가 없을 때 재생성하기 위한 fallback으로만 유지한다.

### CSS

- 다크모드 기반 리포트 테마를 담당한다.
- 전문 증권사 리포트 느낌의 타이포그래피, 히어로, 지표 카드, 표, 뱃지, 섹션 레이아웃을 관리한다.
- 반응형 레이아웃과 테이블 overflow 처리를 일관되게 관리한다.

### JavaScript

- embedded page JSON을 읽고 `view_model` 기반 첫 화면을 렌더링한다.
- 주요 지표 카드와 포트폴리오 테이블의 SVG line sparkline을 생성한다.
- archive UI, source badge, 영향도 badge, Markdown report body 렌더링을 담당한다.
- 필요 시 출처 필터, 섹션 접기/펼치기, 정렬 같은 기능을 추가한다.

## Current Flow

```text
make collect DATE=YYYY-MM-DD
make view-model DATE=YYYY-MM-DD
make analysis-context DATE=YYYY-MM-DD
Codex writes data/reports/YYYY-MM-DD/final.md
make render-html DATE=YYYY-MM-DD REPORT=data/reports/YYYY-MM-DD/final.md
```

The generated HTML embeds page JSON so `file://` and GitHub Pages can render without an extra JSON fetch. `docs/reports/YYYY-MM-DD.json` is also written for debugging and future API-like use.

## Current Design Direction

- Dark brokerage report theme.
- First screen structure: archive header, hero, market indicator cards, portfolio table.
- Main market indicator cards use compact SVG line sparklines with no area fill.
- Portfolio table keeps source badges and compact news/disclosure counts.
- Source badges are symbolic: Naver `N`, DART `D`, yfinance `y`, CNBC `C`.
- Written report sections continue below the dashboard; duplicate H1, metrics table, and portfolio impact table are hidden when `view_model` is available.

## Success Criteria

- 리포트는 GitHub Pages의 `docs/` 정적 배포 방식으로 계속 동작한다.
- 디자인 변경은 CSS 중심으로 가능해야 한다.
- 스파크라인과 UI 인터랙션은 JavaScript로 확장 가능해야 한다.
- Python 렌더러는 구조와 데이터 패키징 중심이어야 한다.
- 데스크톱과 모바일에서 표가 깨지지 않아야 한다.
- `node --check docs/assets/report.js`, `python3 -m py_compile src/render_html.py`, `make test`가 통과해야 한다.

## Screen Planning v0.2

### Product Intent

이 화면은 일반 블로그형 리포트가 아니라, 매일 아침 5분 안에 읽는 개인용 투자 브리핑이다. 사용자는 먼저 시장과 포트폴리오의 상태를 빠르게 파악하고, 이후 필요한 섹터/종목 해석을 읽어야 한다.

화면은 다음 질문에 답해야 한다.

- 오늘 시장 환경은 위험한가, 안정적인가?
- 내 포트폴리오에서 눈에 띄는 종목은 무엇인가?
- 가격 움직임과 수급, 뉴스/공시가 같은 방향인가?
- 더 읽어야 할 뉴스나 공시는 무엇인가?
- 어떤 데이터가 누락됐거나 신뢰도가 낮은가?

### Information Architecture

```text
Archive Header
  -> Hero
  -> Market Snapshot
  -> Portfolio Overview
  -> Insight Briefings
  -> News & Disclosure Digest
  -> Observation Points
  -> Data Quality
```

첫 화면은 정량 데이터 중심이다. 본문 리포트는 첫 화면 이후의 해석 영역으로 둔다.

### Global Rules

- 첫 화면은 `view_model.json`만으로 렌더링한다.
- written report body는 `final.md`에서 온 report JSON으로 렌더링한다.
- `view_model`이 있으면 Markdown의 중복 H1, 주요 거시지표 표, 포트폴리오 영향도 표는 숨긴다.
- 숫자는 화면에서 반복 계산하지 않고, `view_model`에 이미 계산된 값을 우선 사용한다.
- 화면에서 새 사실을 만들지 않는다. 모든 표시값은 `source.json`, `view_model.json`, `final.md` 중 하나에 있어야 한다.
- 출처 뱃지는 포트폴리오/뉴스/공시 맥락에서만 사용한다.

## Screen Modules

### 1. Archive Header

목적:

- 현재 보고 있는 리포트 날짜를 알려준다.
- 최근 5개 리포트로 빠르게 이동한다.
- archive 페이지에서는 돌아가기 링크를 제공한다.

현재 표시:

- `Latest: YYYY-MM-DD KST`
- 최근 5일 링크
- archive 상세 페이지의 `돌아가기`

필수 데이터:

```text
current_date
archive_dates[0..4]
in_archive
```

상호작용:

- 날짜 링크 클릭 시 해당 report HTML로 이동.
- 현재 날짜 링크는 active 상태로 표시.

Fallback:

- archive가 비어 있으면 날짜 링크 영역을 숨긴다.

### 2. Hero

목적:

- 리포트의 정체성과 날짜를 명확히 보여준다.
- “오늘의 브리핑”이라는 첫 인상을 만든다.

현재 표시:

- `KSS MARKET INTELLIGENCE`
- `KO 데일리 브리핑 (YY.MM.DD)`
- `YYYY-MM-DD · 국내외 시장 & 포트폴리오 요약`

필수 데이터:

```text
report.title
view_model.date
view_model.timezone
```

권장 추가 데이터:

```text
view_model.session_label        # 예: "08:00 KST 수집"
view_model.market_status.label  # 예: "주의", "위험", "중립"
view_model.market_status.reason # 한 줄 사유
```

Fallback:

- `report.title`이 없으면 `KO 데일리 브리핑`.
- `date`가 없으면 HTML shell의 `current_date`.

### 3. Market Snapshot

목적:

- 주요 거시지표 8개를 빠르게 비교한다.
- 상승/하락 방향과 최근 7거래일 흐름을 즉시 인지하게 한다.

현재 표시 순서:

```text
KOSPI / KOSDAQ / Nasdaq / S&P 500
VIX / Gold / USD/KRW / 필라델피아반도체지수
```

현재 표시 필드:

- 지표명
- 직전 거래일 종가
- 최신 종가
- 등락률
- 등락폭
- 7거래일 line-only SVG sparkline

필수 데이터:

```text
view_model.market_indicators[].name
view_model.market_indicators[].symbol
view_model.market_indicators[].price.previous_close
view_model.market_indicators[].price.latest_close
view_model.market_indicators[].price.change
view_model.market_indicators[].price.change_pct
view_model.market_indicators[].price.recent_closes
view_model.market_indicators[].as_of_date
view_model.market_indicators[].source
```

권장 추가 데이터:

```text
view_model.market_indicators[].display_order
view_model.market_indicators[].unit           # KRW, USD, index, pct
view_model.market_indicators[].risk_tags      # 예: ["외국인 매도", "환율 상승"]
view_model.market_indicators[].short_comment  # 화면용 한 줄 설명
```

시각 규칙:

- main market cards의 sparkline은 line-only SVG여야 한다.
- area fill, polygon fill, 과한 glow는 사용하지 않는다.
- 상승은 green, 하락은 rose, 중립은 violet 계열.
- 7일 추이는 데이터가 충분할 때만 표시한다.

Fallback:

- 최신 종가가 없으면 `확인 필요`.
- 7거래일 배열이 2개 미만이면 sparkline 대신 `추이 부족`.
- 출처가 없으면 카드 하단이나 tooltip에서 `출처 확인 필요`.

### 4. Portfolio Overview

목적:

- 내 보유 종목별로 가격, 추이, 수급, 뉴스/공시 신호를 한 화면에서 비교한다.
- “오늘 무엇을 더 읽어야 하는가”를 정한다.

현재 표시 컬럼:

```text
종목 / 최신 가격 / 등락 / 추이 (7일) / 수급 / 뉴스·공시
```

현재 표시 필드:

- 종목명
- ticker
- market
- 최신 가격
- 등락률
- 등락폭
- 7거래일 sparkline
- 국내 종목: 외인/기관 최신 순매수·순매도, 7일 외인 합계
- 뉴스 개수
- 공시 개수

필수 데이터:

```text
view_model.holdings[].name
view_model.holdings[].symbol
view_model.holdings[].market
view_model.holdings[].price.latest_close
view_model.holdings[].price.change
view_model.holdings[].price.change_pct
view_model.holdings[].price.recent_closes
view_model.holdings[].flow.latest.foreign
view_model.holdings[].flow.latest.institution
view_model.holdings[].flow.latest.individual
view_model.holdings[].flow.seven_day_total.foreign
view_model.holdings[].flow.seven_day_total.institution
view_model.holdings[].flow.seven_day_total.individual
view_model.holdings[].news[]
view_model.holdings[].disclosures[]
```

권장 추가 데이터:

```text
view_model.holdings[].impact.label          # 긍정, 중립, 부정, 중립~긍정
view_model.holdings[].impact.score          # -2..+2 또는 -100..+100
view_model.holdings[].impact.reasons[]      # 화면용 짧은 근거
view_model.holdings[].primary_issue         # 예: "외인 매도", "AI 기대 부담"
view_model.holdings[].sector
view_model.holdings[].priority              # 화면 정렬용
view_model.holdings[].data_status.price
view_model.holdings[].data_status.flow
view_model.holdings[].data_status.news
```

상호작용 v0.2:

- 행 클릭 시 상세 drawer 또는 inline expand.
- 펼침 영역에는 뉴스/공시 제목, 출처, 링크, 발행일, 관련 가격/수급 해석을 표시.
- 출처 뱃지 클릭 시 해당 출처만 highlight.

Fallback:

- 미국 종목의 국내 수급 컬럼은 `국내 종목만`.
- 최신 가격이 없으면 `확인 필요`와 직전 수집값을 함께 표시.
- 뉴스/공시가 없으면 badge를 숨기거나 `0`으로 표시.

### 5. Insight Briefings

목적:

- 정량 데이터만으로 알 수 없는 해석을 제공한다.
- 사용자가 섹터별로 읽을 수 있게 짧은 단락을 제공한다.

현재 섹션:

```text
Executive Summary
금융주 브리핑
현대차 / 환율
반도체 브리핑
미국 포트폴리오 브리핑
```

데이터 원천:

```text
report.elements from final.md
analysis_context.json 권장
```

권장 추가 데이터:

```text
analysis_context.executive_summary.key_points[]
analysis_context.sectors[].name
analysis_context.sectors[].holdings[]
analysis_context.sectors[].price_summary
analysis_context.sectors[].flow_summary
analysis_context.sectors[].news_summary
analysis_context.sectors[].risks[]
```

화면 규칙:

- 각 섹션은 긴 카드보다 읽기 쉬운 본문 레이아웃을 우선한다.
- 핵심 종목명, 지표명, 리스크 단어는 bold.
- 매수/매도 추천, 목표가, 확정 전망은 표시하지 않는다.

### 6. News & Disclosure Digest

목적:

- 뉴스와 공시를 종목별/출처별로 빠르게 확인하게 한다.
- 포트폴리오 영향도의 근거를 검증할 수 있게 한다.

현재 상태:

- written report body에 요약 텍스트로 표시.
- 포트폴리오 테이블에는 뉴스/공시 개수만 표시.

권장 화면:

```text
종목별 주요 뉴스 1~3개
공시 주요 항목
출처 뱃지
발행일/공시일
원문 링크
관련 영향도
```

필수 데이터:

```text
view_model.news[]
view_model.disclosures[]
view_model.holdings[].news[]
view_model.holdings[].disclosures[]
```

권장 추가 데이터:

```text
news[].published_at
news[].source
news[].title
news[].url
news[].holding_symbols[]
news[].issue_tags[]
news[].summary_short

disclosures[].date
disclosures[].source
disclosures[].title
disclosures[].url
disclosures[].holding_symbols[]
disclosures[].type
disclosures[].summary_short
```

Fallback:

- URL이 없으면 링크 없이 제목만 표시.
- 종목 매핑이 불확실하면 `관련성 확인 필요`.

### 7. Observation Points

목적:

- 사용자가 오늘 체크해야 할 3~5개 포인트를 남긴다.

현재 표시:

- `final.md`의 `오늘의 관찰 포인트`.

권장 데이터:

```text
analysis_context.observation_points[]
```

화면 규칙:

- 체크리스트 카드로 표시할 수 있다.
- 지나치게 긴 문장은 피한다.

### 8. Data Quality

목적:

- 누락, 실패, 대체 데이터 사용을 명확하게 보여준다.
- 리포트 신뢰도를 사용자가 판단할 수 있게 한다.

현재 표시:

- `final.md`의 데이터 품질 섹션.

필수 데이터:

```text
view_model.data_quality[]
view_model.coverage
source.json collectors status
```

권장 화면:

- 정상/주의/실패 상태 pill.
- 실패한 collector 목록.
- 누락된 종목 가격/뉴스/공시.
- 사용자가 알아야 할 한계만 표시하고 내부 API 세부사항은 숨긴다.

Fallback:

- `data_quality`가 비어 있으면 섹션을 생략하거나 `특이사항 없음`.

## Data Model Implications

### Keep `view_model.json` Frontend-Focused

`view_model.json`은 화면을 그리기 위한 데이터만 담는다.

필요한 상위 구조:

```text
schema
date
timezone
as_of
coverage
market_status
market_indicators[]
holdings[]
news[]
disclosures[]
data_quality[]
```

### Add `analysis_context.json`

리포트 본문을 안정적으로 쓰려면 `view_model`과 별도로 Codex 작성용 구조가 필요하다.

권장 구조:

```text
data/reports/YYYY-MM-DD/analysis_context.json
  executive_summary_inputs
  market_context
  sector_contexts[]
  holding_contexts[]
  news_clusters[]
  disclosure_clusters[]
  data_quality_summary
```

역할:

- Codex가 여러 파일을 다시 추론하지 않도록 종목/섹터별 맥락을 묶는다.
- 가격, 수급, 뉴스, 공시를 같은 종목 단위로 연결한다.
- 화면에는 필요 없지만 글 작성에 필요한 근거와 해석 힌트를 담는다.
- 현재 1차 생성기는 `src/build_analysis_context.py`가 담당한다.

## Implementation Phases

### Phase 1. Screen Spec Stabilization

- 현재 문서를 기준으로 화면 모듈을 확정한다.
- 필수 필드와 fallback 문구를 확정한다.
- 주요 지표와 포트폴리오 테이블의 컬럼을 확정한다.

### Phase 2. View Model Schema Update

- `market_status`, `impact`, `primary_issue`, `data_status`, `display_order`를 추가한다.
- 뉴스/공시 객체에 source, url, published_at, issue_tags, summary_short를 일관되게 둔다.

### Phase 3. Analysis Context

- `src/build_analysis_context.py`로 `analysis_context.json`을 만든다.
- Codex automation은 `source.json`, `view_model.json`, `analysis_context.json`, `news.md`를 읽는다.

### Phase 4. Frontend Interaction

- 포트폴리오 row expand.
- 뉴스/공시 drawer.
- 출처 filter/highlight.
- 섹션 anchor navigation.

### Phase 5. Polish

- desktop/tablet/mobile screenshot verification.
- Sparkline line-only QA.
- Text overflow QA.
- GitHub Pages static rendering QA.

## Open Decisions

- 주요 지표 카드에 `시장 위험도` 또는 `리스크 태그`를 표시할지.
- 포트폴리오 행 정렬 기준: 보유 순서, 영향도, 등락률, 데이터 중요도 중 무엇을 우선할지.
- 뉴스/공시 상세를 inline expand로 할지 side drawer로 할지.
- `analysis_context.json`의 sector grouping을 현재 factors 기반으로 충분히 둘지, 별도 sector config를 만들지.
- 미국 종목의 수급 공란을 계속 유지할지, 대체 지표를 둘지.
