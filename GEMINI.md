# AGENTS.md

## Project Goal

Generate a personal morning investment briefing at 08:00 KST.

The system has two responsibilities:
- Python code collects market, portfolio, disclosure, and news inputs.
- Codex Automation reads the collected project files, writes the final report, and renders it as a GitHub Pages HTML report.

## Success Criteria

For each run date:
- `data/incoming/YYYY-MM-DD/source.json` exists.
- `data/incoming/YYYY-MM-DD/news.md` exists.
- `data/reports/YYYY-MM-DD/view_model.json` exists after structured report data is built.
- `data/reports/YYYY-MM-DD/analysis_context.json` exists after report-writing context is built.
- `data/reports/YYYY-MM-DD/final.md` exists after Codex writes the report.
- `docs/index.html`, `docs/reports/YYYY-MM-DD.html`, and `docs/reports/YYYY-MM-DD.json` exist after HTML rendering.

## Reporting Rules

- Do not add facts that are not present in `source.json` or `news.md`.
- Use `view_model.json` as the primary structured source for frontend-ready prices, 7-trading-day closes, investor flows, news, disclosures, and data availability.
- Use `analysis_context.json` as the primary grouped context source for written interpretation when it exists.
- Do not make buy/sell recommendations.
- Do not provide target prices.
- Do not make certain forecasts.
- Mark missing or failed data explicitly.
- Preserve source names and URLs when present.
- Do not include gossip, minor promotional news, or irrelevant events (such as sports sponsorships, casual PR, or stock marketing spams) in the final report. Only report news with corporate value, financial metrics, strategic moves, or regulatory impacts.
- Strictly follow the standard report structure, section names, and table columns defined in [report_format.md](file:///Users/konslie/Desktop/Codex/KSS/config/report_format.md). Never omit, skip, or leave any section incomplete (from section 1 to section 9). The report must be fully generated without placeholders or premature termination.
- Ensure the portfolio impact section is named exactly "## 2. 포트폴리오 영향도" to allow the frontend to correctly filter out duplicate markdown tables.
- Keep the table columns in section 2 exactly as: `| 종목 | 영향도 | 핵심 이슈 | 가격 | 기관 | 외인 | 7일 | 근거 |`.
- Never write operational/management guidelines, template instructions, or formatting explanations (e.g. "주요 항목명과 투자자가 바로 봐야 하는 핵심 단어는 굵게 표시한다.") inside the generated report.


## Engineering Rules

- Keep changes small and directly related to the morning briefing workflow.
- Prefer simple scripts and file-based state for v0.1.
- Keep collectors replaceable: one source failing must not block the whole run.
- Store raw run outputs under `data/incoming/` and final reports under `data/reports/`.
- Store GitHub Pages output under `docs/`.
- Keep frontend assets in `docs/assets/`; `src/render_html.py` should generate static shell pages and embed report/view-model JSON, not handcraft page styling inline.

## Source-specific Integration Rules

### 1. DART Disclosure Collection & Filtering Rules (`src/collect.py`)
- Tier 1 and Tier 2 holdings collect DART disclosures by default. Tier 3 holdings only collect disclosures if `track_disclosure: true` is explicitly configured in `portfolio.yaml`.
- If a holding has `track_disclosure: false`, it is excluded from disclosure collection regardless of its Tier.
- Do not mistake the absence of disclosures for a tracking error if the holding was intentionally excluded or not tracked based on these rules.

### 2. Naver News Query Mapping (`src/collect.py`)
- The system prioritizes `news_query` defined in `portfolio.yaml` for Naver News API search. Only when `news_query` is omitted does it fall back to the default holding name.

### 3. Global Risk Score Rules (`src/build_view_model.py`)
- The Global Risk Score is calculated out of 8 points:
  - US Market (Nasdaq, S&P 500) and VIX have a weight of 2 points each (Total 4 points).
  - KR Market (KOSPI, KOSDAQ) and USD/KRW Exchange Rate have a weight of 1 point each (Total 4 points).
- VIX triggers a risk signal when VIX > 20 or when it surges by more than 10% compared to the previous trading day.
- Risk levels: Score >= 4 is `위험(Red)`, Score >= 2 is `주의(Orange)`, and Score < 2 is `중립(Green)`. Interpret this correctly in the reports.

### 4. Frontend Integration & Table Filtering (`src/render_html.py` & `docs/assets/report.js`)
- The final report must format links as standard markdown: `[Text](URL)`. The frontend parser (`inlineHtml`) automatically converts this into safe HTML links with `target="_blank"`.
- The portfolio impact section name must be exactly `## 2. 포트폴리오 영향도`. If the section name is mismatched, the frontend parser will fail to filter the duplicate markdown table, causing broken layout or double-rendering in the UI.

### 5. Credentials & API Errors (`.env`)
- Collecting data requires `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET`, `DART_API_KEY`, `KRX_ID`, and `KRX_PW` in `.env`. Ensure to explain API credential failure under the "Data Quality" section if collection fails due to missing keys.

