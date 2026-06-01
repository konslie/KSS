# PRD: 한국 주식 정량 밸류에이션 엔진

## 1. 제품 목적

한국 상장기업의 현재 주가가 정량적 가치평가 기준으로 고평가, 저평가, 적정가 중 어디에 위치하는지 판단하는 엔진을 만든다.

사용자는 KOSPI 또는 KOSDAQ 상장사의 종목명이나 종목코드를 입력한다. 시스템은 해당 기업의 재무 데이터, 시장 데이터, 업종 비교 데이터를 수집하고, 기업 유형에 맞는 밸류에이션 모델을 적용해 현재가 대비 적정가 밴드를 산출한다.

최종 목적은 투자 추천이 아니라, 현재 주가의 상대적 비싸고 싼 정도를 정량적으로 판단하는 것이다.

## 2. 대상 시장

대상은 한국 주식시장으로 한정한다.

- KOSPI
- KOSDAQ

분석 제외 대상:

- KONEX
- ETF
- ETN
- 리츠
- 스팩
- 우선주
- 해외 주식
- 비상장 기업

분석 제외 대상은 `UNSUPPORTED`로 처리한다.

## 3. 핵심 질문

엔진은 다음 질문에 답해야 한다.

- 현재 주가는 기업의 이익 대비 비싼가?
- 현재 주가는 기업의 순자산 대비 비싼가?
- 동종 기업과 비교했을 때 비싼가?
- 자기 자신의 과거 밸류에이션 범위와 비교했을 때 비싼가?
- 저평가처럼 보이지만 실적 악화로 인한 value trap 가능성이 있는가?
- 산출된 판단을 얼마나 신뢰할 수 있는가?

## 4. 최종 출력

최종 출력은 다음 구조를 가진다.

- 현재 주가
- 적정가 밴드
  - 보수적 가치
  - 기준 가치
  - 낙관적 가치
- 현재가 대비 상승/하락 여력
- 최종 판정
- 신뢰도
- 모델별 결과
- 주요 리스크 플래그
- 판단 근거 요약

최종 판정 값:

- `UNDERVALUED`
- `FAIRLY_VALUED`
- `OVERVALUED`
- `VALUE_TRAP_RISK`
- `INSUFFICIENT_DATA`
- `UNSUPPORTED`

## 5. 기업 유형 분류

기업은 금융주와 비금융주로 나눈다.

### 5.1 금융주

금융주는 다음 업종을 포함한다.

- 은행
- 보험
- 증권
- 카드
- 캐피탈
- 기타 금융지주

금융주는 자산/부채 구조가 일반 제조업과 다르므로 DCF나 EV/EBITDA보다 다음 모델을 우선 적용한다.

- RIM
- PBR/ROE 기반 평가
- 배당수익률 보조 평가
- Peer PBR 비교
- Historical PBR 비교

### 5.2 비금융주

비금융주는 금융주를 제외한 일반 기업이다.

우선 적용 모델:

- PER 기반 상대가치
- PBR/ROE 보조 평가
- 과거 PER/PBR 비교

v1에서는 DCF를 기본 모델에서 제외한다. DCF는 향후 FCF 데이터 품질과 가정 관리 방식이 안정화된 뒤 선택 모델로 추가한다.

## 6. 입력

필수 입력:

- 종목명 또는 종목코드

예시:

```json
{
  "query": "삼성전자"
}
```

```json
{
  "query": "005930"
}
```

선택 입력:

```json
{
  "query": "005930",
  "valuation_mode": "BASE",
  "as_of_date": "2026-05-29"
}
```

`valuation_mode`:

- `CONSERVATIVE`
- `BASE`
- `AGGRESSIVE`

## 7. 데이터 요구사항

### 7.1 종목 메타데이터

- 종목코드
- 종목명
- 시장 구분
- 업종
- 금융주 여부
- 분석 가능 여부

### 7.2 시장 데이터

- 현재가
- 시가총액
- 발행주식수
- 52주 고가
- 52주 저가
- 최근 거래일
- 거래 정지 여부

### 7.3 재무 데이터

최근 4개 분기 TTM:

- 매출
- 영업이익
- 지배주주순이익
- EPS
- BPS
- ROE
- ROA
- 부채비율
- 영업현금흐름
- CAPEX
- FCF

최근 3년 또는 5년 연간:

- 매출
- 영업이익
- 순이익
- 지배주주순이익
- 자본총계
- 지배주주자본
- EPS
- BPS
- ROE
- DPS
- FCF

## 8. 밸류에이션 모델

### 8.1 금융주 모델

#### RIM

금융주의 핵심 절대가치 모델로 사용한다.

입력:

- BPS
- 최근 3년 평균 ROE
- 요구수익률 Ke
- 초과이익 fade 기간

출력:

- RIM 보수 가치
- RIM 기준 가치
- RIM 낙관 가치

#### PBR/ROE 모델

ROE가 요구수익률보다 높으면 PBR 프리미엄을 정당화할 수 있다.

판단 기준:

- ROE > Ke: PBR 1배 이상 가능
- ROE ~= Ke: PBR 1배 근처
- ROE < Ke: PBR 1배 미만이 합리적

#### 금융주 Peer 모델

동일 금융 업종 내 기업과 비교한다.

- 은행은 은행끼리 비교한다.
- 보험은 보험끼리 비교한다.
- 증권은 증권끼리 비교한다.
- 카드/캐피탈은 카드/캐피탈끼리 비교한다.
- 금융지주는 금융지주 또는 은행과 비교할 수 있다.

사용 지표:

- PBR
- PER
- ROE
- 배당수익률

### 8.2 비금융주 모델

#### PER 상대가치 모델

동종 기업의 PER 중앙값을 기준으로 적정가를 계산한다.

```text
PER 적정가 = 대상 기업 EPS x Peer PER 중앙값
```

적자 기업은 PER 산정에서 제외한다.

#### PBR/ROE 보조 모델

자산가치가 중요한 업종에 보조적으로 사용한다.

```text
PBR 적정가 = 대상 기업 BPS x Peer PBR 중앙값
```

#### Historical Multiple 모델

기업 자기 자신의 과거 밸류에이션 범위와 비교한다.

사용 지표:

- 최근 3년 PER 밴드
- 최근 3년 PBR 밴드
- 최근 5년 PER/PBR 밴드, 데이터 가능 시

산출:

- 현재 PER가 과거 평균 대비 할인인지 프리미엄인지
- 현재 PBR가 과거 평균 대비 할인인지 프리미엄인지
- 현재 밸류에이션이 역사적 하단/중단/상단 중 어디인지

## 9. Peer Group 선정 방식

Peer Group은 대상 기업과 가장 비교 가능성이 높은 3개 기업으로 구성한다.

Peer 선정은 단순 업종 일치가 아니라 다음 과정을 따른다.

1. 후보군 생성
2. 제외 조건 적용
3. Peer Score 계산
4. 점수 상위 3개 선정
5. 유효 Peer 수에 따른 신뢰도 부여

### 9.1 후보군 제외 조건

다음 기업은 Peer 후보에서 제외한다.

- 대상 기업 자신
- 우선주
- 스팩
- 리츠
- ETF/ETN
- 거래정지 또는 관리종목
- 최근 재무 데이터가 부족한 기업
- 시가총액 데이터가 없는 기업

### 9.2 금융주 Peer 선정

금융주는 동일 금융 subtype을 최우선으로 비교한다.

- 은행은 은행과 비교한다.
- 보험은 보험과 비교한다.
- 증권은 증권과 비교한다.
- 카드/캐피탈은 카드/캐피탈과 비교한다.
- 금융지주는 금융지주 또는 은행과 비교할 수 있다.

금융주 Peer 후보는 다음 기준으로 점수화한다.

```text
peer_score =
  financial_subtype_match_score * 45
+ market_cap_similarity_score * 25
+ valuation_metric_availability_score * 15
+ profitability_similarity_score * 10
+ liquidity_score * 5
```

최종적으로 점수 상위 3개 기업을 Peer로 선정한다.

### 9.3 비금융주 Peer 선정

비금융주는 동일 세부 산업을 우선하고, 부족할 경우 대분류 업종으로 확장한다.

비금융주 Peer 후보는 다음 기준으로 점수화한다.

```text
peer_score =
  industry_match_score * 40
+ market_cap_similarity_score * 25
+ valuation_metric_availability_score * 15
+ profitability_similarity_score * 10
+ exchange_similarity_score * 5
+ liquidity_score * 5
```

최종적으로 점수 상위 3개 기업을 Peer로 선정한다.

### 9.4 시가총액 유사도

시가총액 유사도는 대상 기업 대비 후보 기업의 시가총액 비율로 계산한다.

```text
market_cap_ratio = candidate_market_cap / target_market_cap
```

점수 기준:

```text
0.5x ~ 2.0x: 1.0
0.25x ~ 4.0x: 0.7
그 외: 0.3
```

동일 세부 산업 내 후보가 3개 미만이면 시가총액 범위를 완화한다.

### 9.5 Peer 수 부족 시 처리

Peer는 원칙적으로 3개를 선정한다.

유효 Peer 수 기준:

```text
3개: peer_confidence = HIGH
2개: peer_confidence = MEDIUM
1개: peer_confidence = LOW
0개: Peer 모델 제외
```

비금융주 fallback:

```text
Step 1. 세부 산업 동일 + 시총 0.25x~4.0x
Step 2. 세부 산업 동일 + 시총 제한 완화
Step 3. 대분류 업종 동일 + 시총 0.25x~4.0x
Step 4. 대분류 업종 동일 + 시총 제한 완화
Step 5. Peer 모델 제외 또는 LOW 신뢰도 처리
```

금융주 fallback:

```text
Step 1. 금융 subtype 동일 + 시총 0.25x~4.0x
Step 2. 금융 subtype 동일 + 시총 제한 완화
Step 3. 인접 subtype 허용
  - 금융지주 <-> 은행
  - 카드 <-> 캐피탈
Step 4. 금융 전체
Step 5. Peer 모델 제외 또는 LOW 신뢰도 처리
```

### 9.6 Peer 멀티플 계산

선정된 Peer 3개를 기준으로 멀티플을 계산한다.

PER 계산 제외 조건:

- 적자 기업
- PER <= 0
- PER > 100
- 일회성 이익 의심 기업

PBR 계산 제외 조건:

- PBR <= 0
- 자본잠식 기업
- ROE 극단치 기업

3개 Peer 중 일부가 특정 지표에서 제외될 수 있다. 예를 들어 Peer는 3개지만 PER 유효 기업이 2개일 수 있다.

멀티플 산정 방식:

```text
유효 Peer 3개: 중앙값 사용
유효 Peer 2개: 평균값 사용
유효 Peer 1개: 해당 모델 LOW 신뢰도
유효 Peer 0개: 해당 모델 제외
```

## 10. 적정가 밴드 산출

최종 적정가는 하나의 숫자가 아니라 밴드로 산출한다.

```json
{
  "fair_value_band": {
    "low": 61000,
    "base": 70000,
    "high": 82000
  }
}
```

밴드는 모델별 결과를 가중 평균해 만든다. 특정 모델의 데이터 신뢰도가 낮으면 해당 모델의 가중치를 낮추거나 제외한다.

금융주 기본 가중치:

```json
{
  "rim": 0.50,
  "peer_pbr": 0.25,
  "historical_pbr": 0.20,
  "dividend_yield": 0.05
}
```

비금융주 기본 가중치:

```json
{
  "peer_per": 0.40,
  "peer_pbr": 0.20,
  "historical_multiple": 0.40
}
```

## 11. 최종 판정 기준

기준 가치는 `fair_value_band.base`를 사용한다.

```text
upside_pct = (base_fair_value - current_price) / current_price * 100
```

판정 기준:

- `UNDERVALUED`: 상승여력 +20% 이상
- `FAIRLY_VALUED`: -15% 초과 ~ +20% 미만
- `OVERVALUED`: 하락여력 -15% 이하
- `VALUE_TRAP_RISK`: 저평가처럼 보이나 실적/수익성 악화 위험 큼
- `INSUFFICIENT_DATA`: 핵심 데이터 부족
- `UNSUPPORTED`: 분석 제외 대상

`VALUE_TRAP_RISK`는 `UNDERVALUED`보다 우선한다.

## 12. Value Trap 판별

다음 조건 중 복수 충족 시 value trap 위험으로 본다.

- ROE 3년 연속 하락
- 영업이익 2년 연속 감소
- 순이익 2년 연속 감소
- EPS 하락 중 PER만 낮아짐
- FCF 2년 이상 음수
- 부채비율 급등
- 매출 성장 없이 마진만 악화
- PBR은 낮지만 ROE가 Ke보다 낮음
- 일회성 이익으로 순이익이 왜곡됨

예시:

```text
상승여력 +35%이나 ROE 하락, 이익 감소, FCF 악화가 동시에 존재하면 VALUE_TRAP_RISK
```

## 13. 신뢰도 산정

### HIGH

- 핵심 재무 데이터가 모두 존재
- 최근 분기 데이터 확보
- Peer 3개 확보
- 모델별 결과 편차가 과도하지 않음
- 일회성 손익 의심 낮음

### MEDIUM

- 일부 데이터 대체 사용
- Peer 2개 확보
- 일부 모델 제외
- 모델별 결과 편차 큼
- FCF 변동성 있음

### LOW

- 핵심 데이터 누락
- Peer 1개 이하
- 적자 기업
- 턴어라운드 기업
- 일회성 손익 가능성 큼
- 최근 실적 급변

## 14. 출력 스키마

```json
{
  "ticker": "005930",
  "company_name": "삼성전자",
  "market": "KOSPI",
  "sector": "전기전자",
  "company_type": "NON_FINANCIAL",
  "as_of_date": "2026-05-29",
  "current_price": 75000,
  "verdict": "FAIRLY_VALUED",
  "confidence": "MEDIUM",
  "fair_value_band": {
    "low": 68000,
    "base": 79000,
    "high": 91000
  },
  "upside_downside": {
    "to_low_pct": -9.3,
    "to_base_pct": 5.3,
    "to_high_pct": 21.3
  },
  "peer_group": {
    "selected_peers": [
      {
        "ticker": "000660",
        "company_name": "SK하이닉스",
        "reason": "동일 반도체 산업, PBR/ROE 데이터 확보",
        "peer_score": 88.1
      },
      {
        "ticker": "042700",
        "company_name": "한미반도체",
        "reason": "반도체 장비 산업 연관성, 수익성 데이터 확보",
        "peer_score": 75.4
      },
      {
        "ticker": "058470",
        "company_name": "리노공업",
        "reason": "반도체 부품 산업 연관성, 높은 재무 데이터 품질",
        "peer_score": 72.8
      }
    ],
    "peer_confidence": "HIGH"
  },
  "model_results": {
    "peer_per": {
      "fair_value": 81000,
      "weight": 0.40,
      "confidence": "MEDIUM"
    },
    "peer_pbr": {
      "fair_value": 72000,
      "weight": 0.20,
      "confidence": "HIGH"
    },
    "historical_multiple": {
      "fair_value": 78000,
      "weight": 0.40,
      "confidence": "MEDIUM"
    }
  },
  "risk_flags": {
    "value_trap_risk": false,
    "roe_declining": false,
    "earnings_declining": false,
    "fcf_negative": false,
    "high_leverage": false,
    "insufficient_peer_count": false
  },
  "explanation": [
    "현재 주가는 기준 적정가 대비 5.3% 낮아 적정가 범위에 있음",
    "Peer PER 기준으로는 소폭 저평가이나 PBR 기준으로는 적정 수준",
    "과거 밸류에이션 범위와 비교해 중단 수준에 위치함"
  ],
  "data_warnings": []
}
```

## 15. v1 구현 범위

v1에서 구현할 범위:

- KOSPI/KOSDAQ 종목 식별
- 금융주/비금융주 분류
- 현재가 수집
- 최근 재무 데이터 수집
- 금융주 RIM 모델
- 비금융주 PER/PBR 상대가치 모델
- 과거 PER/PBR 비교
- Peer 3개 자동 선정
- 적정가 밴드 산출
- 고평가/저평가/적정 판정
- value trap 플래그
- JSON 출력
- 간단한 Streamlit UI

v1에서 제외:

- DCF 기본 적용
- 뉴스/공시 자연어 분석
- LLM 리포트 생성
- 매수/매도 추천
- 포트폴리오 최적화
- 실시간 수급 분석
- 해외 주식

## 16. 현재 구현 상태

기준일: 2026-06-01

현재 구현은 외부 데이터 수집 전 단계의 테스트 가능한 계산 코어와 application layer에 초점을 둔다.

### 16.1 구현 완료

- Python 패키지 구조
  - `src/kss`
  - `tests`
  - `pyproject.toml`
- 도메인 모델
  - `CompanyMeta`
  - `MarketData`
  - `FinancialData`
  - `PeerCandidate`
  - `SelectedPeer`
  - `FairValueBand`
  - `ModelResult`
  - `RiskFlags`
  - `ValuationResult`
- 판정 enum
  - `UNDERVALUED`
  - `FAIRLY_VALUED`
  - `OVERVALUED`
  - `VALUE_TRAP_RISK`
  - `INSUFFICIENT_DATA`
  - `UNSUPPORTED`
- 금융주/비금융주 분류 모델
- KRX 종목 식별의 최소 계층
  - 종목코드 입력 정규화
  - 종목명 입력 정규화
  - KOSPI/KOSDAQ 지원 여부 판단
  - 우선주/ETF/ETN/리츠/스팩 등 제외 대상 표현
- Peer 선정 로직
  - 후보 점수화
  - 상위 3개 peer 선정
  - peer 수에 따른 신뢰도 산정
- 밸류에이션 계산 로직
  - 비금융주 Peer PER 모델
  - 비금융주 Peer PBR 모델
  - Historical Multiple 모델
  - 금융주 RIM 입력값 반영
  - 금융주 Peer PBR 모델
  - 금융주 Historical PBR 모델
  - 모델별 가중 평균 기반 fair value band 산출
- 리스크 플래그
  - ROE 하락
  - 이익 하락
  - FCF 음수 지속
  - 부채비율 급등
  - value trap risk
  - peer 부족
- 최종 판정 로직
  - 기준 적정가 대비 상승/하락 여력
  - value trap risk 우선 판정
  - confidence 산정
- 데이터 provider 구조
  - `DataProvider` protocol
  - `InMemoryDataProvider`
  - deterministic mock data provider
- application orchestration
  - `analyze_stock(query, provider)`
  - 종목 식별, 데이터 조회, 밸류에이션 계산을 연결
- CLI 초안
  - mock provider 기반 JSON 출력
  - 예: `PYTHONPATH=src .venv/bin/python -m kss.cli 삼성전자`
- 테스트
  - peer 선정 테스트
  - valuation 테스트
  - security master 테스트
  - analysis orchestration 테스트

현재 검증 상태:

```text
16 passed
```

### 16.2 현재 한계

- 실제 KRX, DART, 재무 데이터 API와 아직 연결되어 있지 않다.
- mock data는 구조 검증용이며 실제 투자 판단에 사용할 수 없다.
- 현재 CLI는 mock provider만 사용한다.
- `upside_downside` 별도 출력 필드는 PRD 출력 스키마에 있으나 현재 구현은 explanation과 fair value band 중심이다.
- Streamlit UI는 아직 구현되지 않았다.
- RIM 자체 산식은 provider에서 계산된 `rim_fair_value`를 입력받는 구조이며, 요구수익률/초과이익 fade 계산 엔진은 아직 분리 구현되지 않았다.
- 배당수익률 보조 평가는 금융주 weight table에는 있으나 별도 모델 결과로 아직 산출하지 않는다.
- 외부 데이터 품질 경고 체계는 `data_warnings` 필드만 마련되어 있고, provider별 상세 warning taxonomy는 아직 정의되지 않았다.

## 17. 작업 계획

### 17.1 다음 우선순위

1. 실제 데이터 provider의 첫 버전을 추가한다.
   - 우선 후보: `pykrx` 기반 시장 데이터 provider
   - 목표: 종목 목록, 현재가, 시가총액, 기본 시장 데이터를 가져온다.
   - 검증: provider contract 테스트와 mock fallback 테스트를 통과한다.

2. 재무 데이터 provider를 분리 설계한다.
   - 후보 소스: DART Open API, 재무제표 CSV/캐시, 추후 유료 데이터 provider
   - 목표: EPS, BPS, ROE, 이익/FCF/부채비율 history를 `FinancialData`로 정규화한다.
   - 검증: 누락 데이터가 `INSUFFICIENT_DATA` 또는 confidence 하향으로 반영된다.

3. provider별 데이터 정규화 계층을 추가한다.
   - 종목코드 포맷 통일
   - 시장 구분 통일
   - 업종/금융 subtype 매핑
   - 결측치 및 비정상값 처리

4. CLI를 실제 provider 선택 구조로 확장한다.
   - `--provider mock`
   - `--provider pykrx`
   - `--as-of-date YYYY-MM-DD`
   - JSON 출력 유지

5. 출력 스키마를 PRD와 구현 간 일치시킨다.
   - `upside_downside` 계산 추가
   - peer confidence 출력 추가
   - 모델별 결과의 누락 사유 표현

### 17.2 v1 완성 기준

v1은 다음 조건을 만족하면 완료로 본다.

- 사용자가 종목명 또는 종목코드를 입력할 수 있다.
- KOSPI/KOSDAQ 보통주만 분석 대상으로 처리한다.
- 제외 대상은 `UNSUPPORTED`로 반환한다.
- 핵심 시장 데이터와 재무 데이터가 provider를 통해 주입된다.
- 금융주와 비금융주가 서로 다른 모델 조합으로 평가된다.
- peer 3개 자동 선정 결과가 출력된다.
- fair value band와 최종 판정이 JSON으로 반환된다.
- 데이터 부족, peer 부족, value trap risk가 명시적으로 드러난다.
- 전체 테스트가 통과한다.

### 17.3 v1 이후 후보

- Streamlit UI
- DART 재무제표 캐시 계층
- Historical PER/PBR 자동 계산
- RIM 산식 내재화
- 배당수익률 보조 모델 구현
- 데이터 품질 점수화
- 간단한 HTML/PDF 리포트 출력
- 배치 분석
