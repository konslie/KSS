# Project Memory

Last updated: 2026-06-04 KST

## Context

This project was built from a mobile Codex conversation, but the actual files live on this Mac at:

```text
/Users/konslie/Desktop/Codex/KSS
```

The old KSS project contents were intentionally replaced with the Morning Investment Briefing automation project. The existing `.git` directory was preserved so the repo connection/history remains available.

## Product Direction

Goal: create a personal morning investment briefing system.

Current chosen flow:

```text
Codex Automation at 08:00 KST
  -> make collect
  -> read data/incoming/YYYY-MM-DD/source.json and news.md
  -> Codex writes data/reports/YYYY-MM-DD/final.md
  -> make render-html
  -> publish docs/index.html via GitHub Pages later
```

Important decision: final report writing is done by Codex Automation for now, not by OpenAI API code. The Python code only collects input data and renders Markdown to HTML.

Telegram delivery was removed because Telegram cannot be installed/used on the company Mac. GitHub Pages HTML output is the replacement delivery target.

## Current Project Structure

```text
AGENTS.md
Makefile
README.md
requirements.txt
config/
  automation_prompt.md
  portfolio.yaml
  report_format.md
src/
  collect.py
  render_html.py
tests/
  test_collect.py
  test_render_html.py
data/
  incoming/
  reports/
docs/
  index.html
  reports/
```

## Implemented

- Portfolio config for Korean and US holdings.
- `make collect` creates:
  - `data/incoming/YYYY-MM-DD/source.json`
  - `data/incoming/YYYY-MM-DD/news.md`
- `make render-html` creates:
  - `docs/index.html`
  - `docs/reports/YYYY-MM-DD.html`
- `make test` passes.
- Local `.venv` was created and dependencies were installed.

## Data Sources

Currently working after Codex network approval:

- `yfinance`
  - US holdings: `SCHD`, `SPYM`, `AAPL`, `NVDA`, `CPNG`, `QQQ`, `QQQM`, `RKLB`, `LUNR`
  - Overseas holding news through `yfinance.Ticker(symbol).news`
  - Market indicators:
    - S&P 500: `^GSPC`
    - Nasdaq 100: `^NDX`
    - VIX: `^VIX`
    - SOXX: `SOXX`
    - KOSPI: `^KS11`
    - KOSDAQ: `^KQ11`
    - USD/KRW: `KRW=X`
- Naver Finance HTML parsing
  - Korean holdings prices and change percent
- Naver Search API
  - Korean holding-specific news when `NAVER_CLIENT_ID` and `NAVER_CLIENT_SECRET` are set
- CNBC RSS
  - Global market context news items
  - Reuters RSS was removed because the previous URL returned HTTP 404.

Implemented but requires local secret:

- DART
  - Reads `DART_API_KEY` from environment or `.env`
  - If missing, records:
    - `{"source": "dart", "status": "skipped", "reason": "DART_API_KEY not set"}`
  - Do not ask the user to paste the API key in chat.
  - Preferred-share holdings use common-stock lookup fallbacks where needed, e.g. 현대차2우B `005387` -> 현대차 `005380`.

Installed but not useful as default right now:

- `pykrx`
  - In this environment, installed `pykrx` expects `KRX_ID` / `KRX_PW`.
  - Without those, it is skipped:
    - `{"source": "pykrx", "status": "skipped", "reason": "KRX_ID or KRX_PW not set"}`
  - Default Korean data source remains Naver Finance.

## Secrets Policy

Never put API keys in chat or committed files.

Use local `.env`:

```bash
DART_API_KEY=your_key_here
```

`.env` is ignored by git.

## Useful Commands

Run from:

```bash
cd /Users/konslie/Desktop/Codex/KSS
```

Test:

```bash
make test
```

Offline input generation:

```bash
make collect-offline DATE=2026-06-04
```

Real data collection:

```bash
make collect DATE=2026-06-04
```

Render report HTML after Codex writes `final.md`:

```bash
make render-html DATE=2026-06-04 REPORT=data/reports/2026-06-04/final.md
```

## Last Verified Behavior

For `DATE=2026-06-04`, real collection produced after network approval:

- US quotes: 9
- Korean Naver quotes: 8
- Market indicators: 7
- News: 56 total
  - CNBC RSS: 8
  - Naver Search API: 23
  - yfinance news: 25
- DART disclosures: 25 after `DART_API_KEY` was set, including 현대차2우B through common-stock fallback
- pykrx quotes/indices: 0 because KRX credentials were not set
- Reuters RSS: removed

## Next Priorities

1. Review Naver Search query quality and tighten noisy domestic news matches if needed.
2. Add FRED collector for US macro/rates:
   - US 2Y
   - US 10Y
   - Fed Funds
   - CPI/Core CPI if useful
3. Add report-generation guidance or a sample `final.md` based on real `source.json`.
4. Once data quality is acceptable, connect GitHub Pages:
   - Serve `docs/` from the main branch.
   - Add commit/push step to Codex Automation only after manual runs are reliable.
5. Register Codex Automation for 08:00 KST after the full manual flow works.

## Important Caution

Network failures inside Codex usually happened because the Codex sandbox blocks network by default. When rerun with user-approved escalated network access, `pip install`, `yfinance`, Naver Finance, and CNBC RSS worked.

Do not assume company Mac security policy is blocking everything. So far, the remaining issues are source-specific:

- DART: requires local `.env` key, now configured on this Mac
- pykrx: KRX credentials required by installed library/environment
