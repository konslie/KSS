# KSS 작업 메모리

## 작업 기준

- 기본 작업공간: `/Users/konslie/Desktop/Codex`
- 프로젝트 경로: `/Users/konslie/Desktop/Codex/KSS`
- 공통 지침:
  - `/Users/konslie/Desktop/Codex/AGENTS.md`
  - `/Users/konslie/Desktop/Codex/AGENTS.ko.md`
- 프로젝트 요구사항 기준 문서:
  - `/Users/konslie/Desktop/Codex/KSS/PRD.md`

## 제품 방향

KSS는 한국 주식 정량 밸류에이션 엔진이다.

목표는 KOSPI/KOSDAQ 상장사의 현재 주가가 정량 기준으로 저평가, 적정가, 고평가, value trap risk 중 어디에 해당하는지 판단하는 것이다.

핵심 결정사항:

- 대상 시장은 KOSPI/KOSDAQ으로 한정한다.
- KONEX, ETF, ETN, 리츠, 스팩, 우선주, 해외 주식, 비상장 기업은 제외한다.
- 금융주와 비금융주는 다른 모델로 평가한다.
- 최종 적정가는 단일 숫자가 아니라 `low`, `base`, `high` 밴드로 산출한다.
- Peer 비교 대상은 가장 비교 가능성이 높은 3개 기업만 선정한다.
- v1에서는 DCF를 기본 모델에서 제외한다.

## v1 모델 범위

금융주:

- RIM
- Peer PBR
- Historical PBR
- 배당수익률 보조 평가

비금융주:

- Peer PER
- Peer PBR
- Historical Multiple

최종 판정:

- `UNDERVALUED`
- `FAIRLY_VALUED`
- `OVERVALUED`
- `VALUE_TRAP_RISK`
- `INSUFFICIENT_DATA`
- `UNSUPPORTED`

## Peer 선정 규칙

Peer Group은 대상 기업과 가장 비교 가능성이 높은 3개 기업으로 구성한다.

제외 조건:

- 대상 기업 자신
- 우선주
- 스팩
- 리츠
- ETF/ETN
- 거래정지 또는 관리종목
- 최근 재무 데이터 부족 기업
- 시가총액 데이터가 없는 기업

비금융주 peer score:

```text
peer_score =
  industry_match_score * 40
+ market_cap_similarity_score * 25
+ valuation_metric_availability_score * 15
+ profitability_similarity_score * 10
+ exchange_similarity_score * 5
+ liquidity_score * 5
```

금융주 peer score:

```text
peer_score =
  financial_subtype_match_score * 45
+ market_cap_similarity_score * 25
+ valuation_metric_availability_score * 15
+ profitability_similarity_score * 10
+ liquidity_score * 5
```

Peer 신뢰도:

- 3개: `HIGH`
- 2개: `MEDIUM`
- 1개: `LOW`
- 0개: Peer 모델 제외

## 현재 구현 내역

외부 API 수집 전, 테스트 가능한 순수 계산 코어를 먼저 구현했다.

생성 파일:

- `README.md`
- `pyproject.toml`
- `src/kss/__init__.py`
- `src/kss/models.py`
- `src/kss/peer_selection.py`
- `src/kss/valuation.py`
- `tests/__init__.py`
- `tests/test_peer_selection.py`
- `tests/test_valuation.py`

구현 내용:

- 도메인 enum/dataclass 모델
- 금융주/비금융주 타입
- Peer 후보 점수화
- 상위 3개 Peer 선정
- Peer PER/PBR 멀티플 산정
- 모델별 fair value 계산
- fair value band 조합
- 최종 verdict 산정
- value trap risk 플래그
- confidence 산정
- unsupported/insufficient data 처리

## 검증 내역

실행한 검증:

```bash
python -m compileall src tests
```

결과: 통과

`pytest`는 로컬 기본 Python 환경에 설치되어 있지 않아 실행하지 못했다.

대신 테스트 함수를 직접 실행했다.

```bash
python -c "import sys; sys.path.insert(0, 'src'); import tests.test_peer_selection as p; import tests.test_valuation as v; [getattr(p, name)() for name in dir(p) if name.startswith('test_')]; [getattr(v, name)() for name in dir(v) if name.startswith('test_')]; print('manual tests passed')"
```

결과:

```text
manual tests passed
```

## 환경 메모

- 현재 `/Users/konslie/Desktop/Codex/KSS`는 아직 git repository가 아니다.
- 기본 Python은 `Python 3.10.12`였다.
- Python 3.10 호환을 위해 `StrEnum` 대신 `str, Enum` 조합을 사용했다.
- `pyproject.toml`의 `requires-python`은 `>=3.10`으로 설정했다.

## 다음 작업 후보

1. `git init` 및 첫 커밋 생성
2. `pytest` 개발 의존성 설치 또는 가상환경 구성
3. KRX 종목 식별 계층 추가
4. 외부 데이터 수집 계층 추가
5. 데이터 정규화 계층 추가
6. Streamlit 또는 CLI 인터페이스 추가

