# Codex Automation Prompt

Schedule: `0 8 * * 1-5` in `Asia/Seoul`.

Run this project-scoped automation in `/Users/konslie/Desktop/Codex/KSS`.

Each run:

1. Resolve today's date in Asia/Seoul as `YYYY-MM-DD`.
2. Run `make collect DATE=YYYY-MM-DD`.
3. Read:
   - `data/incoming/YYYY-MM-DD/source.json`
   - `data/incoming/YYYY-MM-DD/news.md`
   - `config/report_format.md`
4. Write the final report to `data/reports/YYYY-MM-DD/final.md`.
5. Run `make render-html DATE=YYYY-MM-DD REPORT=data/reports/YYYY-MM-DD/final.md`.
6. Verify that `docs/index.html` and `docs/reports/YYYY-MM-DD.html` exist.
7. If this directory is a git repository connected to GitHub Pages, commit and push the generated report files.

Report rules:

- Use only facts present in `source.json` and `news.md`.
- Do not recommend buying or selling.
- Do not provide target prices.
- Do not make certain forecasts.
- Preserve source names and URLs when available.
- Mark unclear news as `확인 필요`.
- Include failed collectors and missing data in the Data Quality section.
- If `DART_API_KEY` is missing, do not ask for the key in chat. Report DART as skipped.
- If `KRX_ID` or `KRX_PW` is missing, report pykrx as skipped and rely on Naver Finance plus yfinance market indicators.
- Write the report in Korean.
- Keep it readable in less than 5 minutes.

Success criteria:

- `data/incoming/YYYY-MM-DD/source.json` exists.
- `data/incoming/YYYY-MM-DD/news.md` exists.
- `data/reports/YYYY-MM-DD/final.md` exists.
- `docs/index.html` exists.
- `docs/reports/YYYY-MM-DD.html` exists.
