from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs"
ASSETS_DIR = DOCS_DIR / "assets"
METRIC_ORDER = [
    "KOSPI",
    "KOSDAQ",
    "Nasdaq",
    "Nasdaq 100",
    "S&P 500",
    "VIX",
    "Gold",
    "USD/KRW",
    "필라델피아반도체지수",
    "SOXX",
]


def markdown_to_report(markdown: str, report_date: str | None = None) -> dict[str, Any]:
    elements: list[dict[str, Any]] = []
    lines = markdown.splitlines()
    in_list = False
    table_rows: list[list[str]] = []
    current_section = ""

    def close_blocks() -> None:
        nonlocal in_list, table_rows
        in_list = False
        if table_rows:
            elements.append(table_element(table_rows))
            table_rows = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            close_blocks()
            continue

        if stripped.startswith("|") and stripped.endswith("|"):
            raw_cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if all(re.fullmatch(r":?-{3,}:?", cell) for cell in raw_cells):
                continue
            table_rows.append(raw_cells)
            continue

        close_blocks()

        if stripped.startswith("# "):
            title = format_report_title(stripped[2:], report_date)
            elements.append({"type": "heading", "level": 1, "text": title})
        elif stripped.startswith("## "):
            heading = stripped[3:]
            current_section = heading
            elements.append({"type": "heading", "level": 2, "text": heading})
            if heading == "주요 거시지표" and report_date:
                elements.append({"type": "metrics-meta", "text": metrics_meta_text(report_date)})
        elif stripped.startswith("### "):
            elements.append({"type": "heading", "level": 3, "text": stripped[4:]})
        elif stripped.startswith("- "):
            if not in_list:
                elements.append({"type": "list", "items": [], "autoBold": auto_bold_section(current_section)})
                in_list = True
            elements[-1]["items"].append(stripped[2:])
        elif re.match(r"^\d+\. ", stripped):
            elements.append({"type": "paragraph", "text": stripped, "autoBold": auto_bold_section(current_section)})
        else:
            elements.append({"type": "paragraph", "text": stripped, "autoBold": auto_bold_section(current_section)})

    close_blocks()
    return {
        "schema": "kss-report.v1",
        "date": report_date,
        "title": page_title(report_date),
        "elements": elements,
    }


def table_element(rows: list[list[str]]) -> dict[str, Any]:
    sorted_rows = sort_table_rows(rows)
    if sorted_rows and table_class(sorted_rows[0]) == "portfolio-table":
        sorted_rows = normalize_portfolio_rows(sorted_rows)
    header = sorted_rows[0] if sorted_rows else []
    return {
        "type": "table",
        "className": table_class(header),
        "header": header,
        "rows": sorted_rows[1:],
    }


def sort_table_rows(rows: list[list[str]]) -> list[list[str]]:
    if not rows or table_class(rows[0]) != "metrics-table":
        return rows
    order = {name: index for index, name in enumerate(METRIC_ORDER)}
    header, data_rows = rows[0], rows[1:]
    return [header, *sorted(data_rows, key=lambda row: order.get(row[0], len(order)))]


def normalize_portfolio_rows(rows: list[list[str]]) -> list[list[str]]:
    header = rows[0]
    if "가격" in header:
        return rows
    if not all(name in header for name in ("종가", "등락폭", "등락률")):
        return rows

    close_idx = header.index("종가")
    change_idx = header.index("등락폭")
    pct_idx = header.index("등락률")
    flow_idx = header.index("수급") if "수급" in header else None
    seven_idx = header.index("7일") if "7일" in header else None
    rationale_idx = header.index("근거") if "근거" in header else len(header) - 1
    impact_idx = header.index("영향도")

    normalized = [["종목", "영향도", "가격", "기관", "외인"]]
    if seven_idx is not None:
        normalized[0].append("7일")
    normalized[0].append("근거")

    for row in rows[1:]:
        close = row_value(row, close_idx)
        change = row_value(row, change_idx)
        pct = row_value(row, pct_idx)
        institution, foreign = split_flow(row_value(row, flow_idx) if flow_idx is not None else "")
        normalized_row = [
            row_value(row, 0),
            row_value(row, impact_idx),
            f"{close}\n{change} ({pct})".strip(),
            institution,
            foreign,
        ]
        if seven_idx is not None:
            normalized_row.append(row_value(row, seven_idx))
        normalized_row.append(row_value(row, rationale_idx))
        normalized.append(normalized_row)
    return normalized


def row_value(row: list[str], index: int) -> str:
    return row[index] if 0 <= index < len(row) else ""


def split_flow(text: str) -> tuple[str, str]:
    institution = ""
    foreign = ""
    parts = re.split(r"[,/·]\s*|\s{2,}", text)
    for part in [piece.strip() for piece in parts if piece.strip()]:
        if part.startswith("기관"):
            institution = part
        elif part.startswith("외인") or part.startswith("외국인"):
            foreign = part.replace("외국인", "외인", 1)
    return institution, foreign


def table_class(header_cells: list[str]) -> str:
    header = "|".join(header_cells)
    if "지표" in header and "종가 7일" in header:
        return "metrics-table"
    if "종목" in header and "영향도" in header:
        return "portfolio-table"
    if "주요 헤드라인" in header:
        return "news-table"
    return "data-table"


def auto_bold_section(section: str) -> bool:
    return section in {
        "1. Executive Summary",
        "3. 금융주 브리핑",
        "4. 현대차 / 환율",
        "5. 반도체 브리핑",
        "6. 미국 포트폴리오 브리핑",
    }


def format_report_title(text: str, report_date: str | None = None) -> str:
    date = report_date
    match = re.fullmatch(r"Morning Investment Briefing - (\d{4}-\d{2}-\d{2})", text)
    if match:
        date = match.group(1)
    return page_title(date) if date else text


def page_title(report_date: str | None) -> str:
    if not report_date:
        return "KO_데일리브리핑"
    return f"KO_데일리브리핑({short_date(report_date)})"


def short_date(date: str) -> str:
    match = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", date)
    if not match:
        return date
    return f"{match.group(1)[2:]}.{match.group(2)}.{match.group(3)}"


def metrics_meta_text(report_date: str) -> str:
    return (
        f"{report_date} 08:00 KST 수집 기준입니다. "
        "표시값은 각 시장의 직전 거래일 마감 지표입니다."
    )


def app_shell(
    *,
    title: str,
    report_json: str,
    current_date: str,
    archive_dates: list[str],
    asset_prefix: str = "",
    in_archive: bool = False,
    report_data: dict[str, Any] | None = None,
) -> str:
    archives = html.escape(json.dumps(archive_dates[:5], ensure_ascii=False), quote=True)
    embedded_report = ""
    if report_data is not None:
        payload = (
            json.dumps(report_data, ensure_ascii=False)
            .replace("&", "\\u0026")
            .replace("<", "\\u003c")
            .replace(">", "\\u003e")
        )
        embedded_report = (
            '\n  <script id="report-data" type="application/json">'
            f"{payload}"
            "</script>"
        )
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <link rel="stylesheet" href="{asset_prefix}assets/report.css">
</head>
<body>
  <main id="app"
    data-report-json="{html.escape(report_json)}"
    data-current-date="{html.escape(current_date)}"
    data-archive-dates="{archives}"
    data-in-archive="{str(in_archive).lower()}">
    <section class="app-loading">리포트를 불러오는 중입니다.</section>
  </main>{embedded_report}
  <script src="{asset_prefix}assets/report.js" defer></script>
</body>
</html>
"""


def index_header(
    current_date: str,
    archive_dates: list[str],
    *,
    in_archive: bool = False,
) -> str:
    # Compatibility helper for tests and old callers. The live header is now rendered by JS.
    recent_dates = archive_dates[:5]
    href_prefix = "" if in_archive else "reports/"
    links = "\n".join(
        f'<a href="{href_prefix}{html.escape(date)}.html">{html.escape(date)}</a>'
        for date in recent_dates
    )
    back_link = '<a class="back-link" href="../index.html">돌아가기</a>' if in_archive else ""
    return f"""<section class="brief-header">
        {back_link}
        <p class="brief-title">Latest: {html.escape(current_date)} KST</p>
        <span>최근 5일</span>
        <div class="brief-links">{links}</div>
      </section>"""


def archive_dates(reports_dir: Path) -> list[str]:
    if not reports_dir.exists():
        return []
    return sorted(
        path.stem for path in reports_dir.glob("*.html")
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", path.stem)
    )


def page_data(report_data: dict[str, Any], view_model: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "schema": "kss-page.v1",
        "date": report_data.get("date"),
        "title": report_data.get("title"),
        "report": report_data,
        "view_model": view_model,
    }


def write_frontend_assets() -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    css_path = ASSETS_DIR / "report.css"
    js_path = ASSETS_DIR / "report.js"
    if not css_path.exists():
        css_path.write_text(REPORT_CSS, encoding="utf-8")
    if not js_path.exists():
        js_path.write_text(REPORT_JS, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--view-model", default=None)
    args = parser.parse_args(argv)

    report_path = Path(args.report)
    if not report_path.exists():
        print(f"report not found: {report_path}", file=sys.stderr)
        return 1

    markdown = report_path.read_text(encoding="utf-8")
    report_data = markdown_to_report(markdown, report_date=args.date)
    view_model = None
    if args.view_model:
        view_model_path = Path(args.view_model)
        if view_model_path.exists():
            view_model = json.loads(view_model_path.read_text(encoding="utf-8"))
    packaged_data = page_data(report_data, view_model)
    reports_dir = DOCS_DIR / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    write_frontend_assets()

    dated_path = reports_dir / f"{args.date}.html"
    dated_json_path = reports_dir / f"{args.date}.json"
    index_path = DOCS_DIR / "index.html"

    dates = archive_dates(reports_dir)
    if args.date not in dates:
        dates.append(args.date)
    sorted_dates = sorted(dates, reverse=True)
    title = page_title(args.date)

    dated_json_path.write_text(json.dumps(packaged_data, ensure_ascii=False, indent=2), encoding="utf-8")
    dated_path.write_text(
        app_shell(
            title=title,
            report_json=f"{args.date}.json",
            current_date=args.date,
            archive_dates=sorted_dates,
            asset_prefix="../",
            in_archive=True,
            report_data=packaged_data,
        ),
        encoding="utf-8",
    )
    index_path.write_text(
        app_shell(
            title=title,
            report_json=f"reports/{args.date}.json",
            current_date=args.date,
            archive_dates=sorted_dates,
            report_data=packaged_data,
        ),
        encoding="utf-8",
    )

    print(f"wrote {index_path}")
    print(f"wrote {dated_path}")
    print(f"wrote {dated_json_path}")
    return 0


REPORT_CSS = r"""
:root {
  color-scheme: dark;
  --bg: #08090d;
  --surface: #111520;
  --surface-2: #161b2a;
  --surface-3: #1c2235;
  --text: #eef2fa;
  --muted: #94a3b8;
  --faint: #64748b;
  --line: rgba(255,255,255,0.07);
  --line-2: rgba(255,255,255,0.13);
  --accent: #6366f1;
  --accent-2: #818cf8;
  --gold: #f5c842;
  --gold-dim: #b8922a;
  --up: #4ade80;
  --up-bg: rgba(34,197,94,0.12);
  --up-border: rgba(34,197,94,0.28);
  --down: #fb7185;
  --down-bg: rgba(244,63,94,0.12);
  --down-border: rgba(244,63,94,0.28);
}
* {
  box-sizing: border-box;
}
body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", sans-serif;
  line-height: 1.6;
}
main {
  max-width: 1240px;
  margin: 0 auto;
  padding: 28px 22px 72px;
}

/* ── SHELL ── */
.report-shell {
  position: relative;
}
.report-content {
  position: relative;
}
.app-loading,
.app-error {
  margin: 22px auto;
  padding: 18px;
  border: 0.5px solid var(--line-2);
  border-radius: 12px;
  background: var(--surface);
  color: var(--muted);
}

/* ── NAV HEADER ── */
.brief-header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 10px;
  margin-bottom: 16px;
  padding: 9px 14px;
  border: 0.5px solid var(--line-2);
  border-radius: 12px;
  background: rgba(17, 21, 32, 0.88);
  backdrop-filter: blur(16px);
  color: var(--muted);
  font-size: 13px;
}
.brief-header::before {
  content: "";
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--accent-2);
  flex-shrink: 0;
}
.brief-title {
  margin: 0;
  color: var(--text);
  font-size: 13px;
  font-weight: 600;
}
.brief-links {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-left: auto;
}
.brief-links a,
.back-link {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 12px;
  text-decoration: none;
}
.brief-links a {
  color: var(--accent-2);
  background: rgba(99,102,241,0.14);
  border: 0.5px solid rgba(99,102,241,0.25);
}
.brief-links a:hover {
  background: rgba(99,102,241,0.22);
}
.back-link {
  color: var(--muted);
  background: var(--surface-2);
  font-weight: 600;
  border: 0.5px solid var(--line-2);
}

/* ── VIEW MODEL FRONT PAGE ── */
.data-dashboard {
  position: relative;
}

.dashboard-hero {
  position: relative;
  overflow: hidden;
  margin: 48px 0 34px;
  padding: 42px 44px 38px;
  border: 0.5px solid var(--line-2);
  border-left: 4px solid #f59e0b;
  border-radius: 20px;
  background:
    radial-gradient(circle at 82% 10%, rgba(99,102,241,0.12), transparent 34%),
    linear-gradient(160deg, #151b2a 0%, #101522 48%, #0c101b 100%);
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,0.08),
    0 22px 70px rgba(0,0,0,0.48);
}

.dashboard-hero h1 {
  margin: 0;
  padding: 0;
  border: 0;
  border-radius: 0;
  background: none;
  box-shadow: none;
  color: var(--text);
  font-size: clamp(34px, 4.6vw, 56px);
  line-height: 1.06;
}

.dashboard-hero h1::before {
  display: none;
}

.dashboard-hero p:last-child {
  margin: 22px 0 0;
  color: var(--muted);
  font-size: 17px;
  font-weight: 600;
}

.market-status {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  margin-top: 22px;
  padding: 8px 12px;
  border: 0.5px solid var(--line-2);
  border-radius: 999px;
  background: rgba(148,163,184,0.08);
  color: var(--muted);
  font-size: 13px;
  font-weight: 700;
}

.market-status span {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 2px 10px;
  border-radius: 999px;
  color: #fff;
}

.market-status strong {
  color: var(--muted);
}

.market-status.status-danger span {
  background: rgba(244,63,94,0.22);
  color: var(--down);
}

.market-status.status-warning span {
  background: rgba(245,158,11,0.18);
  color: #fbbf24;
}

.market-status.status-neutral span {
  background: rgba(99,102,241,0.18);
  color: var(--accent-2);
}

.dashboard-section-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  margin: 34px 0 14px;
}

.dashboard-section-head h2 {
  margin: 0;
}

.dashboard-section-head p {
  margin: 10px 0 0;
  color: var(--faint);
  font-size: 13px;
  font-weight: 600;
}

.dashboard-section-head.section-gold h2::before {
  background: #f59e0b;
}

.market-card-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin: 12px 0 34px;
}

.market-card {
  position: relative;
  min-height: 170px;
  padding: 22px;
  border: 1px solid var(--line-2);
  border-radius: 16px;
  background:
    linear-gradient(160deg, #171d2c 0%, #121725 42%, #0f1320 100%);
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,0.08),
    0 10px 32px rgba(0,0,0,0.34);
  overflow: hidden;
}

.market-card::before {
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, #7a1c2e, #f43f5e, #9a2038);
}

.market-card.market-up::before {
  background: linear-gradient(90deg, #0f5e2a, #2ddb6e, #0f7a34);
}

.market-card.market-neutral::before {
  background: linear-gradient(90deg, #2d2d8a, #818cf8, #3a3aaa);
}

.market-copy p {
  margin: 0 0 14px;
  color: var(--faint);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.prev-value {
  display: block;
  margin-bottom: 12px;
  color: rgba(148,163,184,0.8);
  font-size: 14px;
  font-weight: 600;
}

.market-copy strong {
  display: block;
  margin-bottom: 12px;
  color: var(--text);
  font-size: clamp(30px, 3vw, 42px);
  font-weight: 750;
  line-height: 1;
  letter-spacing: -0.02em;
  font-variant-numeric: tabular-nums;
}

.metric-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.metric-pills b,
.metric-pills em {
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  padding: 4px 13px;
  border-radius: 999px;
  font-size: 14px;
  font-style: normal;
  font-weight: 750;
}

.market-up .metric-pills b {
  border: 0.5px solid var(--up-border);
  background: var(--up-bg);
  color: var(--up);
}

.market-down .metric-pills b {
  border: 0.5px solid var(--down-border);
  background: var(--down-bg);
  color: var(--down);
}

.metric-pills em {
  border: 0.5px solid var(--line-2);
  background: rgba(148,163,184,0.1);
  color: var(--muted);
}

.market-comment {
  display: inline-flex;
  margin-top: 10px;
  color: var(--muted);
  font-size: 12px;
  font-weight: 700;
}

.tag-list,
.status-flags {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin-top: 8px;
}

.tag-list i,
.status-flags i {
  display: inline-flex;
  align-items: center;
  min-height: 22px;
  padding: 2px 7px;
  border: 0.5px solid var(--line-2);
  border-radius: 999px;
  background: rgba(148,163,184,0.08);
  color: var(--faint);
  font-size: 11px;
  font-style: normal;
  font-weight: 650;
}

.status-flags i {
  border-color: rgba(245,158,11,0.26);
  background: rgba(245,158,11,0.1);
  color: #fbbf24;
}

.market-spark {
  position: absolute;
  right: 18px;
  bottom: 18px;
  opacity: 0.9;
  pointer-events: none;
}

.numeric-spark {
  display: block;
  width: 122px;
  height: 46px;
  overflow: visible;
}

.numeric-baseline {
  fill: none;
  stroke: rgba(148,163,184,0.16);
  stroke-width: 1;
  stroke-dasharray: 3 6;
}

.numeric-path {
  fill: none;
  stroke-width: 2.1;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.numeric-path-shadow {
  display: none;
}

.numeric-dot {
  stroke: rgba(8,9,13,0.94);
  stroke-width: 2;
}

.spark-up .numeric-path {
  stroke: var(--up);
}

.spark-up .numeric-dot {
  stroke: var(--up);
  fill: var(--up);
}

.spark-down .numeric-path {
  stroke: var(--down);
}

.spark-down .numeric-dot {
  stroke: var(--down);
  fill: var(--down);
}

.spark-neutral .numeric-path {
  stroke: var(--accent-2);
}

.spark-neutral .numeric-dot {
  stroke: var(--accent-2);
  fill: var(--accent-2);
}

.holding-matrix {
  margin: 12px 0 34px;
  overflow-x: auto;
  border: 0.5px solid var(--line-2);
  border-radius: 16px;
  background: rgba(10,13,20,0.9);
}

.holding-data-table {
  width: 100%;
  min-width: 1320px;
  border-collapse: collapse;
  font-size: 14px;
}

.holding-data-table th,
.holding-data-table td {
  border-bottom: 0.5px solid var(--line);
  padding: 18px 20px;
  text-align: left;
  vertical-align: middle;
}

.holding-data-table th {
  background: var(--surface-2);
  color: var(--faint);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.holding-data-table tr:last-child td {
  border-bottom: 0;
}

.holding-data-table td:first-child strong {
  display: block;
  color: var(--text);
  font-size: 16px;
  font-weight: 750;
}

.holding-data-table td:first-child span {
  display: block;
  margin-top: 4px;
  color: var(--faint);
  font-size: 12px;
}

.change-pill {
  display: inline-flex;
  min-width: 76px;
  justify-content: center;
  padding: 4px 11px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 800;
}

.change-up {
  border: 0.5px solid var(--up-border);
  background: var(--up-bg);
  color: var(--up);
}

.change-down {
  border: 0.5px solid var(--down-border);
  background: var(--down-bg);
  color: var(--down);
}

.change-neutral {
  border: 0.5px solid var(--line-2);
  background: rgba(148,163,184,0.1);
  color: var(--muted);
}

.change-detail {
  display: block;
  margin-top: 7px;
  color: var(--muted);
  font-size: 12px;
}

.impact-pill {
  display: inline-flex;
  min-width: 74px;
  justify-content: center;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
  white-space: nowrap;
}

.impact-up {
  border: 0.5px solid var(--up-border);
  background: var(--up-bg);
  color: var(--up);
}

.impact-down {
  border: 0.5px solid var(--down-border);
  background: var(--down-bg);
  color: var(--down);
}

.impact-neutral {
  border: 0.5px solid var(--line-2);
  background: rgba(148,163,184,0.1);
  color: var(--muted);
}

.issue-cell {
  min-width: 180px;
}

.issue-cell strong {
  display: block;
  color: var(--text);
  font-size: 13px;
  font-weight: 750;
}

.compact-flow {
  display: grid;
  gap: 5px;
  min-width: 180px;
}

.compact-flow span {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  color: var(--muted);
  font-size: 12px;
}

.compact-flow b {
  color: var(--faint);
}

.compact-flow small {
  color: var(--faint);
}

.flow-up {
  color: var(--up) !important;
}

.flow-down {
  color: var(--down) !important;
}

.info-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}

.info-pills span {
  display: inline-flex;
  min-height: 28px;
  align-items: center;
  padding: 3px 10px;
  border: 0.5px solid var(--line-2);
  border-radius: 999px;
  background: rgba(148,163,184,0.08);
  color: var(--muted);
  font-size: 12px;
  font-weight: 650;
}

.brief-summary {
  max-width: 260px;
  margin: 0;
  color: var(--muted);
  font-size: 12px;
  font-weight: 650;
  line-height: 1.45;
}

.muted-cell {
  color: var(--faint);
  font-size: 12px;
}

/* ── HERO (h1) ── */
h1 {
  position: relative;
  overflow: hidden;
  margin: 0 0 28px;
  padding: 32px 32px 28px;
  border: 0.5px solid var(--line-2);
  border-left: 3px solid var(--gold);
  border-radius: 16px;
  background:
    linear-gradient(160deg, #1e2236 0%, #141826 50%, #0e1120 100%);
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,0.08),
    0 20px 60px rgba(0,0,0,0.5);
  color: var(--text);
  font-size: clamp(32px, 5vw, 58px);
  font-weight: 700;
  line-height: 1.06;
  letter-spacing: -0.02em;
}
h1::before {
  content: "개인 포트폴리오 관련 브리핑";
  display: block;
  margin-bottom: 14px;
  color: var(--gold);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.14em;
}

/* ── SECTION H2 ── */
h2 {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 36px 0 14px;
  padding: 0;
  border: none;
  background: none;
  color: var(--text);
  font-size: 16px;
  font-weight: 600;
  letter-spacing: -0.01em;
}
h2::before {
  content: "";
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--accent-2);
  flex-shrink: 0;
}
h2::after {
  content: "";
  flex: 1;
  height: 0.5px;
  background: var(--line-2);
  margin-left: 4px;
}
h3 {
  margin: 20px 0 8px;
  font-size: 15px;
  font-weight: 600;
  color: var(--text);
}
p, li {
  font-size: 14px;
  color: #c8d6e8;
}
p {
  margin: 0 0 12px;
}
ul {
  margin: 0 0 12px;
  padding-left: 20px;
}

/* ── METRICS META ── */
.metrics-meta {
  margin: -4px 0 12px;
  color: var(--faint);
  font-size: 12px;
}

/* ── METRICS TABLE → CARD GRID ── */
.data-table {
  width: 100%;
  border-collapse: collapse;
  margin: 12px 0 22px;
  font-size: 13px;
  overflow: hidden;
  border-radius: 12px;
  background: var(--surface);
  border: 0.5px solid var(--line-2);
}
.data-table th,
.data-table td {
  border-bottom: 0.5px solid var(--line);
  padding: 10px 14px;
  text-align: left;
  vertical-align: middle;
}
.data-table tr:last-child td {
  border-bottom: none;
}
.data-table th {
  background: var(--surface-2);
  color: var(--faint);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  border-bottom: 0.5px solid var(--line-2);
}
.data-table tbody tr:hover td {
  background: rgba(255,255,255,0.025);
}

/* ── METRICS CARD GRID ── */
.metrics-table {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  border: none;
  background: none;
  border-radius: 0;
  overflow: visible;
  margin: 12px 0 22px;
}
.metrics-table tr,
.metrics-table td {
  display: block;
}
.metrics-table tbody {
  display: contents;
}
.metrics-table thead {
  display: none;
}
.metrics-table tr {
  position: relative;
  padding: 18px;
  border: 1px solid var(--line-2);
  border-radius: 14px;
  background:
    linear-gradient(160deg, #1e2438 0%, #141824 40%, #0f1320 100%);
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,0.10),
    inset 0 -1px 0 rgba(0,0,0,0.4),
    inset 1px 0 0 rgba(255,255,255,0.05),
    0 8px 28px rgba(0,0,0,0.5);
  overflow: hidden;
}
.metrics-table tr::before {
  content: "";
  position: absolute;
  top: 0; left: 10%; right: 10%;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.22), transparent);
  pointer-events: none;
}
.metrics-table tr::after {
  content: "";
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 2px;
  background: linear-gradient(90deg, #7c6018, var(--gold), #9a7a20);
  border-radius: 14px 14px 0 0;
}
.metrics-table td {
  border: none;
  padding: 0;
}

/* col 1: label */
.metrics-table td:nth-child(1) {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.09em;
  text-transform: uppercase;
  color: var(--faint);
  margin-bottom: 14px;
}
/* col 2: prev value */
.metrics-table td:nth-child(2) {
  font-size: 11px;
  color: rgba(100,116,139,0.8);
  margin-bottom: 0;
}
.metrics-table td:nth-child(2)::before {
  content: "전일 ";
}
/* col 3: current value + sparkline row */
.metrics-table td:nth-child(3) {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 8px;
  margin-top: 4px;
  margin-bottom: 12px;
}
.metric-value-text {
  font-size: 22px;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: #eef2fa;
  line-height: 1;
  text-shadow: 0 1px 4px rgba(0,0,0,0.6);
}
/* sparkline inside metric card */
.metric-spark {
  flex-shrink: 0;
  display: block;
}
/* col 4 & 5: change badges */
.metrics-table td:nth-child(4),
.metrics-table td:nth-child(5) {
  display: inline-flex;
  align-items: center;
  margin-right: 5px;
  padding: 3px 9px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
}
.metrics-table td:nth-child(6) {
  margin-top: 10px;
  display: block;
}

/* badge colour based on content via JS class injection */
.metrics-table tr.metric-up td:nth-child(4) {
  background: var(--up-bg);
  color: var(--up);
  border: 0.5px solid var(--up-border);
}
.metrics-table tr.metric-down td:nth-child(4) {
  background: var(--down-bg);
  color: var(--down);
  border: 0.5px solid var(--down-border);
}
.metrics-table td:nth-child(5) {
  background: rgba(148,163,184,0.1);
  color: var(--muted);
  border: 0.5px solid var(--line-2);
}

/* ── PORTFOLIO PANEL ── */
.portfolio-panel {
  position: relative;
  margin: 12px 0 22px;
  overflow-x: auto;
  padding: 10px 0 6px;
  border-radius: 12px;
  background: var(--surface);
  border: 0.5px solid var(--line-2);
}
.portfolio-panel .portfolio-table {
  min-width: 1060px;
  margin-top: 8px;
  margin-bottom: 0;
  border: none;
  background: none;
  border-radius: 0;
}
.portfolio-table td:nth-child(1) {
  font-weight: 600;
  white-space: nowrap;
  color: var(--text);
}
.portfolio-table td:nth-child(3),
.portfolio-table td:nth-child(4),
.portfolio-table td:nth-child(5) {
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}
.portfolio-table th:first-child,
.portfolio-table td:first-child {
  position: sticky;
  left: 0;
  z-index: 2;
  background: var(--surface);
}
.portfolio-table th:first-child {
  z-index: 3;
  background: var(--surface-2);
}
.portfolio-table th,
.portfolio-table td {
  vertical-align: middle;
}

/* ── SOURCE LEGEND ── */
.source-legend {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 6px 10px;
  margin: 0 8px 8px;
  color: var(--faint);
  font-size: 11px;
}
.source-legend span {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

/* ── IMPACT LEGEND ── */
.impact-legend {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin-top: 10px;
  font-size: 12px;
}
.impact-legend span {
  padding: 8px 12px;
  border: 0.5px solid var(--line-2);
  border-radius: 10px;
  background: var(--surface-2);
  color: var(--muted);
}
.impact-legend strong {
  margin-right: 4px;
  color: var(--text);
}

/* ── SOURCE BADGES ── */
.source-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 17px;
  height: 17px;
  margin: 0 2px;
  border-radius: 50%;
  color: #fff;
  font-size: 10px;
  font-weight: 800;
  line-height: 1;
  vertical-align: -2px;
}
.source-badge:first-child { margin-left: 0; }
.source-naver   { background: #16a34a; }
.source-dart    { background: #2563eb; }
.source-yfinance{ background: #7c3aed; }
.source-cnbc    { background: #0d9488; }

/* ── NEWS TABLE ── */
.news-table td:first-child {
  width: 140px;
  font-weight: 600;
  color: var(--accent-2);
  font-size: 12px;
}

/* ── SPARKLINES (portfolio table) ── */
.spark {
  white-space: nowrap;
  min-width: 120px;
}
.sparkline {
  display: block;
  width: 110px;
  height: 44px;
  overflow: visible;
}
.sparkline-baseline {
  stroke: rgba(148,163,184,0.3);
  stroke-width: 1;
  stroke-dasharray: 4 5;
}
.sparkline-fill {
  opacity: 0.15;
}
.sparkline-path {
  fill: none;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.sparkline-dot {
  stroke: rgba(8,9,13,0.9);
  stroke-width: 2;
}
.sparkline-up  { color: #4ade80; }
.sparkline-down{ color: #fb7185; }
.sparkline-path,
.sparkline-dot {
  stroke: currentColor;
  fill: currentColor;
}
.sparkline-up   .sparkline-fill { fill: #4ade80; }
.sparkline-down .sparkline-fill { fill: #fb7185; }

/* ── VALUE COLOURS ── */
.value-up   { color: var(--up); }
.value-down { color: var(--down); }

/* ── TONE PILLS ── */
.tone-up, .tone-down, .tone-neutral {
  display: inline-flex;
  align-items: center;
  min-width: 52px;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  text-align: center;
  white-space: nowrap;
  justify-content: center;
}
.tone-up {
  background: var(--up-bg);
  color: var(--up);
  border: 0.5px solid var(--up-border);
}
.tone-down {
  background: var(--down-bg);
  color: var(--down);
  border: 0.5px solid var(--down-border);
}
.tone-neutral {
  background: rgba(148,163,184,0.1);
  color: var(--muted);
  border: 0.5px solid var(--line-2);
}

/* ── RESPONSIVE ── */
@media (max-width: 900px) {
  .metrics-table {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .market-card-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .dashboard-hero {
    margin-top: 28px;
    padding: 34px 30px 30px;
  }
  .dashboard-section-head {
    align-items: flex-start;
    flex-direction: column;
  }
}
@media (max-width: 640px) {
  main { padding: 14px 10px 36px; }
  h1 { padding: 24px 20px 20px; font-size: 26px; }
  .brief-header {
    top: 8px;
  }
  .dashboard-hero {
    margin: 24px 0 28px;
    padding: 28px 22px 24px;
    border-radius: 16px;
  }
  .dashboard-hero h1 {
    font-size: 30px;
  }
  .dashboard-hero p:last-child {
    font-size: 14px;
  }
  .market-card-grid {
    grid-template-columns: 1fr;
  }
  .market-card {
    min-height: 164px;
  }
  .metrics-table { grid-template-columns: 1fr; }
  .data-table:not(.metrics-table) {
    display: block;
    overflow-x: auto;
  }
  .impact-legend { grid-template-columns: 1fr; }
}

"""


REPORT_JS = r"""
const SOURCE_BADGES = [
  ["Naver Search News", "N", "naver", "Naver Search"],
  ["Naver Search", "N", "naver", "Naver Search"],
  ["DART", "D", "dart", "DART"],
  ["yfinance news", "y", "yfinance", "yfinance"],
  ["yfinance 뉴스", "y", "yfinance", "yfinance"],
  ["yfinance", "y", "yfinance", "yfinance"],
  ["CNBC Markets", "C", "cnbc", "CNBC"],
  ["CNBC", "C", "cnbc", "CNBC"],
].sort((a, b) => b[0].length - a[0].length);

const AUTO_BOLD_TERMS = [
  "오늘의 한줄 요약", "시장 위험도", "핵심 이벤트 3건",
  "하나금융지주", "우리금융지주", "DB손해보험", "현대차2우B",
  "삼성전자", "이수페타시스", "현대바이오", "금호석유화학",
  "SCHD", "Apple", "Nvidia", "Coupang", "Rocket Lab", "Resolve AI",
  "Intuitive Machines", "USD/KRW", "KOSPI", "KOSDAQ", "Nasdaq 100",
  "Nasdaq", "S&P 500", "SOXX", "VIX", "DART", "Naver Search",
  "yfinance", "CNBC", "주의", "확인 필요", "약세", "강세", "상승",
  "하락", "리스크",
].sort((a, b) => b.length - a.length);

const SPARK_VALUES = { "▁": 1, "▂": 2, "▃": 3, "▄": 4, "▅": 5, "▆": 6, "▇": 7, "█": 8 };

document.addEventListener("DOMContentLoaded", () => {
  const app = document.querySelector("#app");
  if (!app) return;
  loadReport(app).catch((error) => {
    app.innerHTML = `<section class="app-error">리포트를 불러오지 못했습니다: ${escapeHtml(error.message)}</section>`;
  });
});

async function loadReport(app) {
  const page = await readReportData(app);
  const report = page.report || page;
  const viewModel = page.view_model || null;
  const archives = JSON.parse(app.dataset.archiveDates || "[]");
  const inArchive = app.dataset.inArchive === "true";
  app.innerHTML = "";
  app.append(renderShell(report, app.dataset.currentDate, archives, inArchive, viewModel));
  document.title = report.title || "KO 데일리 브리핑";
}

async function readReportData(app) {
  const embedded = document.querySelector("#report-data");
  if (embedded && embedded.textContent.trim()) {
    return JSON.parse(embedded.textContent);
  }
  const response = await fetch(app.dataset.reportJson, { cache: "no-store" });
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  return response.json();
}

function renderShell(report, currentDate, archives, inArchive, viewModel) {
  const shell = document.createElement("article");
  shell.className = "report-shell";
  shell.append(renderHeader(currentDate, archives, inArchive));
  if (viewModel) shell.append(renderDataDashboard(viewModel, report));
  const content = document.createElement("section");
  content.className = "report-content";
  const elements = viewModel ? reportBodyElements(report.elements || []) : report.elements || [];
  for (const element of elements) {
    content.append(renderElement(element));
  }
  shell.append(content);
  return shell;
}

function reportBodyElements(elements) {
  const visible = [];
  let skipSection = null;
  for (const element of elements) {
    if (element.type === "heading" && element.level === 1) continue;
    if (element.type === "heading" && element.level === 2) {
      const text = element.text || "";
      if (text.includes("주요 거시지표") || text.includes("포트폴리오 영향도")) {
        skipSection = text;
        continue;
      }
      skipSection = null;
    }
    if (skipSection) {
      if (element.type === "table" || element.type === "metrics-meta") continue;
    }
    visible.push(element);
  }
  return visible;
}

function renderHeader(currentDate, archives, inArchive) {
  const header = document.createElement("section");
  header.className = "brief-header";
  if (inArchive) {
    const back = document.createElement("a");
    back.className = "back-link";
    back.href = "../index.html";
    back.textContent = "돌아가기";
    header.append(back);
  }
  const title = document.createElement("p");
  title.className = "brief-title";
  title.textContent = `Latest: ${currentDate} KST`;
  header.append(title);
  const label = document.createElement("span");
  label.textContent = "최근 5일";
  header.append(label);
  const links = document.createElement("div");
  links.className = "brief-links";
  const prefix = inArchive ? "" : "reports/";
  for (const date of archives.slice(0, 5)) {
    const link = document.createElement("a");
    link.href = `${prefix}${date}.html`;
    link.textContent = date;
    links.append(link);
  }
  header.append(links);
  return header;
}

function renderDataDashboard(viewModel, report) {
  const section = document.createElement("section");
  section.className = "data-dashboard";
  section.append(renderHero(report, viewModel));
  section.append(renderSectionHeader("주요 지표", `기준: ${escapeHtml(viewModel.date || report.date || "")} 장 마감`, "violet"));
  section.append(renderMarketCards(viewModel.market_indicators || []));
  section.append(renderSectionHeader("포트폴리오 현황", "", "gold", sourceLegend()));
  section.append(renderHoldingMatrix(viewModel.holdings || []));
  return section;
}

function renderHero(report, viewModel) {
  const hero = document.createElement("section");
  hero.className = "dashboard-hero";
  const date = viewModel.date || report.date || "";
  const status = viewModel.market_status || {};
  const statusTone = marketStatusTone(status.label);
  hero.innerHTML = `
    <p class="eyebrow">개인 포트폴리오 관련 브리핑</p>
    <h1>${escapeHtml(report.title || "KO 데일리 브리핑")}</h1>
    <p>${escapeHtml(date)} · 국내외 시장 & 포트폴리오 요약</p>
    <div class="market-status status-${statusTone}">
      <span>${escapeHtml(status.label || "상태 확인")}</span>
      <strong>${escapeHtml(status.reason || "시장 상태 산정 정보 부족")}</strong>
    </div>
  `;
  return hero;
}

function renderSectionHeader(title, meta = "", accent = "violet", addon = null) {
  const head = document.createElement("div");
  head.className = `dashboard-section-head section-${accent}`;
  head.innerHTML = `
    <div>
      <h2>${escapeHtml(title)}</h2>
      ${meta ? `<p>${meta}</p>` : ""}
    </div>
  `;
  if (addon) head.append(addon);
  return head;
}

function renderMarketCards(indicators) {
  const grid = document.createElement("div");
  grid.className = "market-card-grid";
  for (const indicator of indicators) {
    const price = indicator.price || {};
    const tone = toneFromNumber(price.change_pct);
    const card = document.createElement("article");
    card.className = `market-card market-${tone}`;
    card.innerHTML = `
      <div class="market-copy">
        <p>${escapeHtml(indicator.name || indicator.symbol || "")}</p>
        <span class="prev-value">이전 ${formatPlainNumber(price.previous_close)}</span>
        <strong>${formatPlainNumber(price.latest_close)}</strong>
        <span class="metric-pills"><b>${formatSignedPercent(price.change_pct)}</b><em>${formatSignedNumber(price.change)}</em></span>
        <span class="market-comment">${escapeHtml(indicator.short_comment || "")}</span>
        ${tagList(indicator.risk_tags || [])}
      </div>
      <div class="market-spark">${numericSparkline(price.recent_closes || [], tone)}</div>
    `;
    grid.append(card);
  }
  return grid;
}

function renderHoldingMatrix(holdings) {
  const wrap = document.createElement("section");
  wrap.className = "holding-matrix";

  const table = document.createElement("table");
  table.className = "holding-data-table";
  table.innerHTML = `
    <thead>
      <tr>
        <th>종목</th>
        <th>최신 가격</th>
        <th>등락</th>
        <th>추이 (7일)</th>
        <th>수급</th>
        <th>영향</th>
        <th>핵심 이슈</th>
        <th>한줄 요약</th>
      </tr>
    </thead>
  `;
  const tbody = document.createElement("tbody");
  for (const holding of holdings) {
    const price = holding.price || {};
    const flow = holding.flow || {};
    const latest = flow.latest || {};
    const seven = flow.seven_day_total || {};
    const tone = toneFromNumber(price.change_pct);
    const hasDomesticFlow = holding.market === "KR";
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>
        <strong>${escapeHtml(holding.name || "")}</strong>
        <span>${escapeHtml(holding.symbol || "")} · ${escapeHtml(holding.market || "")}</span>
      </td>
      <td>${formatHoldingPrice(price.latest_close, holding.market)}</td>
      <td>
        <span class="change-pill change-${tone}">${formatSignedPercent(price.change_pct)}</span>
        <span class="change-detail">${formatSignedNumber(price.change, holding.market)}</span>
      </td>
      <td>${numericSparkline(price.recent_closes || [], tone)}</td>
      <td>${hasDomesticFlow ? compactFlowBlock(latest, seven) : `<span class="muted-cell">국내 종목만</span>`}</td>
      <td><span class="impact-pill impact-${impactTone(holding.impact?.label)}">${escapeHtml(holding.impact?.label || "중립")}</span></td>
      <td>
        <div class="issue-cell">
          <strong>${escapeHtml(holding.primary_issue || "특이 신호 제한")}</strong>
          ${tagList((holding.impact?.reasons || []).slice(0, 2))}
          ${dataStatusFlags(holding.data_status || {})}
        </div>
      </td>
      <td><p class="brief-summary">${escapeHtml(holdingBriefSummary(holding))}</p></td>
    `;
    tbody.append(tr);
  }
  table.append(tbody);
  wrap.append(table);
  return wrap;
}

function holdingBriefSummary(holding) {
  const news = holding.news || [];
  const article = news.find((item) => item.title || item.summary);
  if (article) {
    return truncateText(`뉴스: ${article.title || article.summary}`, 74);
  }
  return "확인된 뉴스 없음";
}

function truncateText(text, limit) {
  const normalized = String(text || "").replace(/\s+/g, " ").trim();
  if (normalized.length <= limit) return normalized;
  return `${normalized.slice(0, limit - 1)}…`;
}

function tagList(tags) {
  const clean = (tags || []).filter(Boolean).slice(0, 3);
  if (!clean.length) return "";
  return `<span class="tag-list">${clean.map((tag) => `<i>${escapeHtml(tag)}</i>`).join("")}</span>`;
}

function dataStatusFlags(status) {
  const labels = [];
  if (status.price === "missing") labels.push("가격 확인 필요");
  if (status.flow === "missing") labels.push("수급 확인 필요");
  if (status.news === "empty") labels.push("뉴스 없음");
  if (!labels.length) return "";
  return `<span class="status-flags">${labels.map((label) => `<i>${escapeHtml(label)}</i>`).join("")}</span>`;
}

function impactTone(label) {
  const text = String(label || "");
  if (text.includes("긍정")) return "up";
  if (text.includes("부정")) return "down";
  return "neutral";
}

function marketStatusTone(label) {
  if (label === "위험") return "danger";
  if (label === "주의") return "warning";
  return "neutral";
}

function compactFlowBlock(latest, seven) {
  const foreign = latest.foreign;
  const institution = latest.institution;
  const sevenForeign = seven?.available ? seven.foreign : null;
  return `
    <div class="compact-flow">
      <span class="flow-${toneFromNumber(foreign)}"><b>외인</b>${formatFlow(foreign)}</span>
      <span class="flow-${toneFromNumber(institution)}"><b>기관</b>${formatFlow(institution)}</span>
      ${Number.isFinite(Number(sevenForeign)) ? `<small>7일 외인 ${formatFlow(sevenForeign)}</small>` : ""}
    </div>
  `;
}

function flowBlock(flow) {
  const items = [
    ["기관", flow.institution],
    ["외인", flow.foreign],
    ["개인", flow.individual],
  ];
  return `<div class="flow-stack">${items.map(([label, value]) => {
    const tone = toneFromNumber(value);
    return `<span class="flow-item flow-${tone}"><b>${label}</b>${formatFlow(value)}</span>`;
  }).join("")}</div>`;
}

function renderElement(element) {
  if (element.type === "heading") {
    const heading = document.createElement(`h${element.level}`);
    heading.innerHTML = inlineHtml(element.text, { autoBold: false, sourceBadges: false });
    return heading;
  }
  if (element.type === "metrics-meta") {
    const meta = document.createElement("p");
    meta.className = "metrics-meta";
    meta.textContent = element.text;
    return meta;
  }
  if (element.type === "paragraph") {
    const paragraph = document.createElement("p");
    paragraph.innerHTML = inlineHtml(element.text, { autoBold: element.autoBold, sourceBadges: false });
    return paragraph;
  }
  if (element.type === "list") {
    const list = document.createElement("ul");
    for (const item of element.items || []) {
      const li = document.createElement("li");
      li.innerHTML = inlineHtml(item, { autoBold: element.autoBold, sourceBadges: false });
      list.append(li);
    }
    return list;
  }
  if (element.type === "table") {
    return renderTable(element);
  }
  return document.createTextNode("");
}

function renderTable(element) {
  if (element.className === "portfolio-table") {
    const panel = document.createElement("section");
    panel.className = "portfolio-panel";
    panel.append(sourceLegend());
    panel.append(tableNode(element));
    panel.append(impactLegend());
    return panel;
  }
  return tableNode(element);
}

function tableNode(element) {
  const table = document.createElement("table");
  table.className = `data-table ${element.className}`.trim();
  const thead = document.createElement("thead");
  const headRow = document.createElement("tr");
  for (const cell of element.header || []) {
    const th = document.createElement("th");
    th.textContent = cell;
    headRow.append(th);
  }
  thead.append(headRow);
  table.append(thead);
  const tbody = document.createElement("tbody");
  for (const row of element.rows || []) {
    const tr = document.createElement("tr");
    row.forEach((cell, index) => {
      const td = document.createElement("td");
      const classes = cellClasses(cell);
      const tableClasses = classes.filter((name) => !name.startsWith("tone-"));
      if (tableClasses.length) td.className = tableClasses.join(" ");
      const isPortfolioRationale = element.className === "portfolio-table" && index > 0;
      const header = element.header[index] || "";
      if (element.className === "portfolio-table" && header === "가격") {
        td.append(renderPriceCell(cell));
      } else if (classes.includes("spark")) {
        td.append(renderSparkline(cell, sparklineTone(row)));
      } else {
        td.innerHTML = wrapTone(
          inlineHtml(cell, { autoBold: false, sourceBadges: isPortfolioRationale }),
          classes,
        );
      }
      tr.append(td);
    });
    tbody.append(tr);
  }
  table.append(tbody);
  return table;
}

function renderPriceCell(text) {
  const raw = String(text || "");
  const [close, detail = ""] = raw.split(/\n|<br\s*\/?>/i, 2);
  const tone = detail.trim().startsWith("-") ? "down" : detail.trim().startsWith("+") ? "up" : "neutral";
  const wrap = document.createElement("div");
  wrap.className = `price-stack price-${tone}`;
  const closeNode = document.createElement("span");
  closeNode.className = "price-close";
  closeNode.textContent = close.trim();
  const detailNode = document.createElement("span");
  detailNode.className = "price-change";
  detailNode.textContent = detail.trim();
  wrap.append(closeNode);
  if (detail.trim()) wrap.append(detailNode);
  return wrap;
}

function inlineHtml(text, { autoBold, sourceBadges }) {
  let result = escapeHtml(text || "");
  result = result.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  if (autoBold) result = autoBoldKeywords(result);
  if (sourceBadges) result = sourceBadgeHtml(result);
  return result;
}

function autoBoldKeywords(text) {
  const protectedStrong = [];
  let result = text.replace(/<strong>.*?<\/strong>/g, (match) => {
    protectedStrong.push(match);
    return `@@STRONG_${protectedStrong.length - 1}@@`;
  });
  AUTO_BOLD_TERMS.forEach((term, index) => {
    result = result.split(escapeHtml(term)).join(`@@AUTO_BOLD_${index}@@`);
  });
  AUTO_BOLD_TERMS.forEach((term, index) => {
    result = result.split(`@@AUTO_BOLD_${index}@@`).join(`<strong>${escapeHtml(term)}</strong>`);
  });
  protectedStrong.forEach((value, index) => {
    result = result.split(`@@STRONG_${index}@@`).join(value);
  });
  return result;
}

function sourceBadgeHtml(text) {
  let result = text;
  const replacements = [];
  SOURCE_BADGES.forEach(([label, initial, sourceClass, title], index) => {
    const token = `@@SOURCE_BADGE_${index}@@`;
    result = result.split(escapeHtml(label)).join(token);
    replacements.push([
      token,
      `<span class="source-badge source-${sourceClass}" title="${escapeHtml(title)}">${escapeHtml(initial)}</span>`,
    ]);
  });
  for (const [token, badge] of replacements) {
    result = result.split(token).join(badge);
  }
  return result;
}

function cellClasses(text) {
  const classes = [];
  if (/[▁▂▃▄▅▆▇█]{3,}/.test(text)) classes.push("spark");
  if (/^\+|\+\d/.test(text)) classes.push("value-up");
  else if (/^-|-\d/.test(text)) classes.push("value-down");
  if (text === "긍정") classes.push("tone-up");
  else if (text === "부정") classes.push("tone-down");
  else if ((text || "").startsWith("중립")) classes.push("tone-neutral");
  return classes;
}

function wrapTone(cell, classes) {
  for (const tone of ["tone-up", "tone-down", "tone-neutral"]) {
    if (classes.includes(tone)) return `<span class="${tone}">${cell}</span>`;
  }
  return cell;
}

function sparklineTone(row) {
  for (const cell of row) {
    const trimmed = String(cell || "").trim();
    if (trimmed.startsWith("+")) return "up";
    if (trimmed.startsWith("-")) return "down";
  }
  return "up";
}

function renderSparkline(text, tone) {
  const values = [...String(text || "")].filter((char) => SPARK_VALUES[char]).map((char) => SPARK_VALUES[char]);
  if (!values.length) {
    const span = document.createElement("span");
    span.textContent = text;
    return span;
  }
  const width = 116;
  const height = 46;
  const padX = 7;
  const padY = 7;
  const usableW = width - padX * 2;
  const usableH = height - padY * 2;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = Math.max(max - min, 1);
  const step = usableW / Math.max(values.length - 1, 1);
  const points = values.map((value, index) => {
    const x = padX + step * index;
    const normalized = (value - min) / span;
    const y = padY + usableH - normalized * usableH;
    return [x, y];
  });
  const path = points.map(([x, y], index) => `${index === 0 ? "M" : "L"}${x.toFixed(1)} ${y.toFixed(1)}`).join(" ");
  const fillPoints = [
    `${points[0][0].toFixed(1)},${(height - padY).toFixed(1)}`,
    ...points.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`),
    `${points[points.length - 1][0].toFixed(1)},${(height - padY).toFixed(1)}`,
  ].join(" ");
  const [lastX, lastY] = points[points.length - 1];
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("class", `sparkline sparkline-${tone || (values[values.length - 1] >= values[0] ? "up" : "down")}`);
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", "7일 추이");
  svg.innerHTML = `
    <line class="sparkline-baseline" x1="${padX}" y1="${height - padY}" x2="${width - padX}" y2="${height - padY}"></line>
    <polygon class="sparkline-fill" points="${fillPoints}"></polygon>
    <path class="sparkline-path" d="${path}"></path>
    <circle class="sparkline-dot" cx="${lastX.toFixed(1)}" cy="${lastY.toFixed(1)}" r="4"></circle>
  `;
  return svg;
}

function numericSparkline(values, tone = "neutral") {
  const nums = values.map((value) => Number(value)).filter((value) => Number.isFinite(value));
  if (!nums.length) return `<span class="muted-cell">미수집</span>`;
  const width = 122;
  const height = 46;
  const padX = 8;
  const padY = 8;
  const min = Math.min(...nums);
  const max = Math.max(...nums);
  const span = Math.max(max - min, 1);
  const usableW = width - padX * 2;
  const usableH = height - padY * 2;
  const step = usableW / Math.max(nums.length - 1, 1);
  const coords = nums.map((value, index) => {
    const x = padX + step * index;
    const y = padY + usableH - ((value - min) / span) * usableH;
    return [x, y];
  });
  const path = coords.map(([x, y], index) => `${index === 0 ? "M" : "L"}${x.toFixed(1)} ${y.toFixed(1)}`).join(" ");
  const [lastX, lastY] = coords[coords.length - 1];
  return `
    <svg class="numeric-spark spark-${tone}" viewBox="0 0 ${width} ${height}" aria-hidden="true">
      <path class="numeric-baseline" d="M${padX} ${(height - padY).toFixed(1)} H${(width - padX).toFixed(1)}"></path>
      <path class="numeric-path numeric-path-shadow" d="${path}"></path>
      <path class="numeric-path" d="${path}"></path>
      <circle class="numeric-dot" cx="${lastX.toFixed(1)}" cy="${lastY.toFixed(1)}" r="2.8"></circle>
    </svg>
  `;
}

function toneFromNumber(value) {
  const number = Number(value);
  if (!Number.isFinite(number) || number === 0) return "neutral";
  return number > 0 ? "up" : "down";
}

function formatPlainNumber(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "확인 필요";
  return number.toLocaleString("ko-KR", { maximumFractionDigits: 2 });
}

function formatHoldingPrice(value, market) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "확인 필요";
  if (market === "US") return `$${number.toLocaleString("en-US", { maximumFractionDigits: 2 })}`;
  return `${number.toLocaleString("ko-KR", { maximumFractionDigits: 0 })}원`;
}

function formatSignedNumber(value, market) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "확인 필요";
  const sign = number > 0 ? "+" : "";
  if (market === "US") return `${sign}$${number.toLocaleString("en-US", { maximumFractionDigits: 2 })}`;
  return `${sign}${number.toLocaleString("ko-KR", { maximumFractionDigits: 0 })}`;
}

function formatSignedPercent(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "확인 필요";
  const sign = number > 0 ? "+" : "";
  return `${sign}${number.toLocaleString("ko-KR", { maximumFractionDigits: 2 })}%`;
}

function formatFlow(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "미수집";
  const direction = number > 0 ? "순매수" : number < 0 ? "순매도" : "중립";
  const abs = Math.abs(number);
  if (abs >= 1000000000000) {
    return `${direction} ${(abs / 1000000000000).toLocaleString("ko-KR", { maximumFractionDigits: 1 })}조`;
  }
  return `${direction} ${Math.round(abs / 100000000).toLocaleString("ko-KR")}억`;
}

function sourceLegend() {
  const legend = document.createElement("div");
  legend.className = "source-legend";
  legend.setAttribute("aria-label", "뉴스 출처 범례");
  for (const [initial, sourceClass, label] of [
    ["N", "naver", "Naver Search"],
    ["D", "dart", "DART"],
    ["y", "yfinance", "yfinance"],
    ["C", "cnbc", "CNBC"],
  ]) {
    const item = document.createElement("span");
    item.innerHTML = `<span class="source-badge source-${sourceClass}">${initial}</span>${escapeHtml(label)}`;
    legend.append(item);
  }
  return legend;
}

function impactLegend() {
  const legend = document.createElement("div");
  legend.className = "impact-legend";
  legend.setAttribute("aria-label", "영향도 기준");
  legend.innerHTML = `
    <span><strong>긍정</strong> 가격/공시/뉴스 흐름이 보유 종목에 우호적</span>
    <span><strong>중립</strong> 방향성이 제한적이거나 확인 필요</span>
    <span><strong>부정</strong> 가격 약세나 리스크 뉴스가 우세</span>
  `;
  return legend;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
"""


if __name__ == "__main__":
    sys.exit(main())
