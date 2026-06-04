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
- `data/reports/YYYY-MM-DD/final.md` exists after Codex writes the report.
- `docs/index.html` and `docs/reports/YYYY-MM-DD.html` exist after HTML rendering.

## Reporting Rules

- Do not add facts that are not present in `source.json` or `news.md`.
- Do not make buy/sell recommendations.
- Do not provide target prices.
- Do not make certain forecasts.
- Mark missing or failed data explicitly.
- Preserve source names and URLs when present.

## Engineering Rules

- Keep changes small and directly related to the morning briefing workflow.
- Prefer simple scripts and file-based state for v0.1.
- Keep collectors replaceable: one source failing must not block the whole run.
- Store raw run outputs under `data/incoming/` and final reports under `data/reports/`.
- Store GitHub Pages output under `docs/`.
