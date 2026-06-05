# KSS Data Schema

## Purpose

This project separates raw collection, frontend rendering data, report-writing context, written Markdown, and deployed page JSON.

```text
source.json
  -> view_model.json
  -> analysis_context.json
  -> final.md
  -> docs/reports/YYYY-MM-DD.json
```

## `data/incoming/YYYY-MM-DD/source.json`

Role: collected source snapshot.

This file keeps the broad output from collectors. It may contain raw-ish source data, normalized collector fields, failed collector notes, news, disclosures, portfolio config, and market data.

Primary consumers:

- `src/build_view_model.py`
- Codex report writing as fact backup

Core top-level fields:

```text
date
as_of
timezone
portfolio[]
market_data
news[]
disclosures[]
data_quality[]
```

Rules:

- Do not remove collector failure information.
- Do not hide missing data.
- Prefer preserving source names and URLs.
- This file may be messy; downstream files should make it easier to use.

## `data/reports/YYYY-MM-DD/view_model.json`

Role: frontend-ready data.

This file should contain the values needed to render the first-screen dashboard and key UI states. It should not be overloaded with long-form reasoning.

Primary consumers:

- `docs/assets/report.js`
- `src/build_analysis_context.py`
- Codex report writing for structured facts

Core top-level fields:

```text
schema
date
as_of
timezone
market_status
market_indicators[]
holdings[]
market_flows[]
news[]
disclosures[]
data_quality[]
coverage
```

### `market_status`

```text
label       # 위험, 주의, 중립
score
reasons[]
reason
```

### `market_indicators[]`

```text
name
symbol
source
as_of_date
display_order
unit
risk_tags[]
short_comment
price.latest_close
price.previous_close
price.close_7d_ago
price.recent_closes[]
price.change
price.change_pct
price.trend
volume
```

Rules:

- `recent_closes` should preserve numeric values for SVG line sparklines.
- Main market indicator sparklines are line-only; do not require area fill data.
- `display_order` should match the intended screen order.

### `holdings[]`

```text
name
symbol
market
tier
sector
priority
factors[]
price
flow.latest
flow.seven_day_total
news[]
disclosures[]
impact.label
impact.score
impact.reasons[]
primary_issue
data_status.price
data_status.flow
data_status.news
data_status.disclosures
analysis_inputs
```

Rules:

- `impact` is a screen-level summary, not an investment recommendation.
- `primary_issue` should be short enough for a table cell.
- `data_status` drives fallback display such as `확인 필요`.
- US holdings should use `flow: not_applicable` when Korean investor flow does not apply.

## `data/reports/YYYY-MM-DD/analysis_context.json`

Role: Codex writing context.

This file groups market, sector, holding, news, disclosure, and data-quality context so Codex can write `final.md` with less inference from raw files.

Primary consumers:

- Codex automation
- Future report-writing tools

Core top-level fields:

```text
schema
date
as_of
timezone
executive_summary_inputs
market_context
sector_contexts[]
holding_contexts[]
news_clusters[]
disclosure_clusters[]
data_quality_summary
```

Rules:

- This file may repeat facts from `view_model.json`, but grouped for writing.
- It should not include buy/sell recommendations, target prices, or certain forecasts.
- It should keep source names and URLs where available.

## `data/reports/YYYY-MM-DD/final.md`

Role: written interpretation.

This file is produced by Codex using `source.json`, `view_model.json`, `analysis_context.json`, `news.md`, and report guidelines.

Rules:

- Use only facts present in project data files.
- Do not make buy/sell recommendations.
- Do not provide target prices.
- Do not make certain forecasts.
- Focus on Executive Summary, sector briefings, news/disclosure interpretation, observation points, and data quality.
- Do not over-repeat the first-screen quantitative UI.

## `docs/reports/YYYY-MM-DD.json`

Role: packaged deploy JSON.

This file is written by `src/render_html.py` and contains report JSON plus `view_model` for debugging and future API-like use.

Shape:

```text
schema = kss-page.v1
date
title
report
view_model
```

Rules:

- The generated HTML embeds the same page JSON to support GitHub Pages and direct static viewing.
- Frontend should read embedded JSON first, then fallback to fetching this file.
