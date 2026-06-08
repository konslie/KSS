# Codex Automation Prompt

Schedule: `0 8 * * 1-5` in `Asia/Seoul`.

Run this project-scoped automation in `/Users/konslie/Desktop/Codex/KSS`.

Each run:

1. Resolve today's date in Asia/Seoul as `YYYY-MM-DD`.
2. Run `make collect DATE=YYYY-MM-DD`.
3. Run `make view-model DATE=YYYY-MM-DD`.
4. Run `make analysis-context DATE=YYYY-MM-DD`.
5. Read:
   - `data/incoming/YYYY-MM-DD/source.json`
   - `data/reports/YYYY-MM-DD/view_model.json`
   - `data/reports/YYYY-MM-DD/analysis_context.json`
   - `data/incoming/YYYY-MM-DD/news.md`
   - `config/report_format.md`
6. Write the final report to `data/reports/YYYY-MM-DD/final.md`.
7. Run `make render-html DATE=YYYY-MM-DD REPORT=data/reports/YYYY-MM-DD/final.md`.
8. Verify that `docs/index.html`, `docs/reports/YYYY-MM-DD.html`, and `docs/reports/YYYY-MM-DD.json` exist.
9. If this directory is a git repository connected to GitHub Pages, commit and push the generated report files and frontend assets under `docs/`.

Report rules:

- Use only facts present in `source.json` and `news.md`.
- Use `view_model.json` as the primary structured input for prices, 7-day closes, flows, news, disclosures, and data availability.
- Use `analysis_context.json` as the primary grouped context for Executive Summary, sector briefings, observation points, and data-quality interpretation.
- The frontend renders the main hero, market indicators, portfolio status table, source badges, and line sparklines from `view_model.json`; `final.md` should focus on written interpretation and concise rationale.
- Do not write sector briefings as a list of price changes. For each sector, explain how news, disclosures, and investor flows affect the portfolio names, using `analysis_context.sector_contexts[].interpretation_cues` and `holding_contexts[].interpretation_cues` when available.
- Treat price as evidence, not the conclusion. A useful paragraph should answer: what the news/disclosure issue is, whether foreign/institutional flow confirms or conflicts with the price move, and what risk or observation point follows for the portfolio.
- Keep `data/` outputs as local run artifacts. Do not commit `data/incoming/` or `data/reports/`.
- Commit only deployable report artifacts under `docs/`: `docs/index.html`, `docs/reports/YYYY-MM-DD.html`, `docs/reports/YYYY-MM-DD.json`, and changed `docs/assets/` files.
- Do not recommend buying or selling.
- Do not provide target prices.
- Do not make certain forecasts.
- Preserve source names and URLs when available.
- Mark unclear news as `확인 필요`.
- If the only available fact is a price move, explicitly say that the signal is limited instead of padding the briefing with repeated price narration.
- In portfolio impact rationale, mention the source names and briefly state the actual issue behind the news or disclosure. Keep it concise, but do not stop at generic wording such as "AI/semiconductor issue".
- In the portfolio impact table, use columns: 종목, 영향도, 가격, 기관, 외인, 7일, 근거.
- For 가격, write `종가<br>등락폭 (등락률)`. Keep positive changes with `+` and negative changes with `-`.
- For 기관 and 외인, include domestic 순매수/순매도 direction and a compact scale when available. Leave US/Nasdaq holdings blank in those columns.
- Use `최근 종가` or `전일 종가` for collected closing prices. Do not call collected close data `최신 가격` because the report is not real time.
- Use Markdown bold for key labels and important terms in Executive Summary and each sector briefing.
- Include user-relevant failed collectors and missing data in the Data Quality section.
- If `DART_API_KEY` is missing, do not ask for the key in chat. Report DART as skipped.
- If optional KRX reference data is unavailable, state that some KRX reference data was not collected. Do not expose `KRX_AUTH_KEY`, fallback, parser, cache, or API internals in the user-facing report.
- Write the report in Korean.
- Keep it readable in less than 5 minutes.

Success criteria:

- `data/incoming/YYYY-MM-DD/source.json` exists.
- `data/incoming/YYYY-MM-DD/news.md` exists.
- `data/reports/YYYY-MM-DD/view_model.json` exists.
- `data/reports/YYYY-MM-DD/analysis_context.json` exists.
- `data/reports/YYYY-MM-DD/final.md` exists.
- `docs/index.html` exists.
- `docs/reports/YYYY-MM-DD.html` exists.
- `docs/reports/YYYY-MM-DD.json` exists.
