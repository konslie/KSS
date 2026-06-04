# KSS Report Frontend Redesign Plan

## Goal

현재 리포트 페이지는 Python 렌더러가 HTML, CSS, UI 요소를 대부분 문자열로 직접 생성한다. 이 구조는 빠르게 정적 리포트를 만들기에는 좋지만, 전문 증권사 리포트 같은 고급 프론트엔드 디자인과 인터랙션을 확장하기에는 한계가 있다.

목표는 `docs/` 정적 배포 방식을 유지하면서, 리포트 화면을 CSS와 JavaScript 중심의 프론트엔드 구조로 개선하는 것이다.

## Recommended Structure

```text
docs/
  assets/
    report.css
    report.js
  index.html
  reports/
    YYYY-MM-DD.html

src/
  render_html.py
```

## Responsibilities

### Python Renderer

- Markdown 또는 수집 데이터를 의미 있는 HTML 구조로 변환한다.
- 섹션, 표, 행, 셀, 출처, 수치 같은 semantic markup 생성을 담당한다.
- 시각 디자인, 애니메이션, 복잡한 인터랙션은 최소화한다.

### CSS

- 다크모드 기반 리포트 테마를 담당한다.
- 전문 증권사 리포트 느낌의 타이포그래피, 표, 뱃지, 스파크라인, 섹션 레이아웃을 관리한다.
- 반응형 레이아웃과 테이블 overflow 처리를 일관되게 관리한다.

### JavaScript

- 스파크라인 렌더링 또는 보강을 담당한다.
- archive UI, 테이블 하이라이트, 행 hover/focus, 모바일 보정 같은 인터랙션을 담당한다.
- 필요 시 출처 필터, 섹션 접기/펼치기, 정렬 같은 기능을 추가한다.

## Migration Path

1. `render_html.py`의 인라인 `<style>`을 `docs/assets/report.css`로 분리한다.
2. HTML 템플릿에서 `report.css`와 `report.js`를 로드하도록 변경한다.
3. 스파크라인, 출처 뱃지, archive 동작처럼 프론트엔드 성격이 강한 부분을 JavaScript로 이동한다.
4. Python 렌더러는 데이터와 문서 구조 생성에 집중하도록 단순화한다.
5. 기존 `docs/index.html`과 `docs/reports/*.html` 정적 배포 방식은 유지한다.

## Current Design Direction

- Dark finance terminal theme
- Professional brokerage report mood
- Dense but readable portfolio table
- Symbolic source badges only in portfolio impact sections
- SVG line sparklines with baseline, area fill, and terminal dot
- Bold emphasis for key report terms in executive and sector briefings

## Success Criteria

- 리포트는 GitHub Pages의 `docs/` 정적 배포 방식으로 계속 동작한다.
- 디자인 변경은 CSS 중심으로 가능해야 한다.
- 스파크라인과 UI 인터랙션은 JavaScript로 확장 가능해야 한다.
- Python 렌더러는 이전보다 짧고 구조 중심이어야 한다.
- 데스크톱과 모바일에서 표가 깨지지 않아야 한다.
