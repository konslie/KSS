from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs"
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
SOURCE_BADGES = [
    ("Naver Search News", "N", "naver", "Naver Search"),
    ("Naver Search", "N", "naver", "Naver Search"),
    ("DART", "D", "dart", "DART"),
    ("yfinance news", "y", "yfinance", "yfinance"),
    ("yfinance 뉴스", "y", "yfinance", "yfinance"),
    ("yfinance", "y", "yfinance", "yfinance"),
    ("CNBC Markets", "C", "cnbc", "CNBC"),
    ("CNBC", "C", "cnbc", "CNBC"),
]
SPARK_VALUES = {
    "▁": 1,
    "▂": 2,
    "▃": 3,
    "▄": 4,
    "▅": 5,
    "▆": 6,
    "▇": 7,
    "█": 8,
}
AUTO_BOLD_SECTIONS = {
    "1. Executive Summary",
    "3. 금융주 브리핑",
    "4. 현대차 / 환율",
    "5. 반도체 브리핑",
    "6. 미국 포트폴리오 브리핑",
}
AUTO_BOLD_TERMS = [
    "오늘의 한줄 요약",
    "시장 위험도",
    "핵심 이벤트 3건",
    "하나금융지주",
    "우리금융지주",
    "DB손해보험",
    "현대차2우B",
    "삼성전자",
    "이수페타시스",
    "현대바이오",
    "금호석유화학",
    "SCHD",
    "Apple",
    "Nvidia",
    "Coupang",
    "Rocket Lab",
    "Resolve AI",
    "Intuitive Machines",
    "USD/KRW",
    "KOSPI",
    "KOSDAQ",
    "Nasdaq 100",
    "Nasdaq",
    "S&P 500",
    "SOXX",
    "VIX",
    "DART",
    "Naver Search",
    "yfinance",
    "CNBC",
    "주의",
    "확인 필요",
    "약세",
    "강세",
    "상승",
    "하락",
    "리스크",
]


def markdown_to_html(markdown: str, report_date: str | None = None) -> str:
    lines = markdown.splitlines()
    output: list[str] = []
    in_list = False
    table_rows: list[list[str]] = []
    current_section = ""

    def close_blocks() -> None:
        nonlocal in_list, table_rows
        if in_list:
            output.append("</ul>")
            in_list = False
        if table_rows:
            output.extend(render_table(table_rows))
            table_rows = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            close_blocks()
            continue

        if stripped.startswith("|") and stripped.endswith("|"):
            raw_cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in raw_cells):
                continue
            if not table_rows:
                close_blocks()
            table_rows.append(raw_cells)
            continue

        close_blocks()

        if stripped.startswith("# "):
            output.append(f"<h1>{format_report_title(stripped[2:], report_date)}</h1>")
        elif stripped.startswith("## "):
            heading = stripped[3:]
            current_section = heading
            output.append(f"<h2>{format_inline(heading)}</h2>")
            if heading == "주요 거시지표" and report_date:
                output.append(metrics_meta(report_date))
        elif stripped.startswith("### "):
            output.append(f"<h3>{format_inline(stripped[4:])}</h3>")
        elif stripped.startswith("- "):
            if not in_list:
                output.append("<ul>")
                in_list = True
            output.append(f"<li>{format_inline(stripped[2:], auto_bold=auto_bold_section(current_section))}</li>")
        elif re.match(r"^\d+\. ", stripped):
            output.append(f"<p>{format_inline(stripped, auto_bold=auto_bold_section(current_section))}</p>")
        else:
            output.append(f"<p>{format_inline(stripped, auto_bold=auto_bold_section(current_section))}</p>")

    close_blocks()
    return "\n".join(output)


def auto_bold_section(section: str) -> bool:
    return section in AUTO_BOLD_SECTIONS


def format_inline(
    text: str,
    source_badges: bool = False,
    auto_bold: bool = False,
) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    if auto_bold:
        escaped = auto_bold_keywords(escaped)
    if source_badges:
        escaped = format_source_badges(escaped)
    return escaped


def auto_bold_keywords(escaped: str) -> str:
    protected: list[str] = []

    def protect(match: re.Match[str]) -> str:
        protected.append(match.group(0))
        return f"@@STRONG_{len(protected) - 1}@@"

    escaped = re.sub(r"<strong>.*?</strong>", protect, escaped)
    terms = sorted(AUTO_BOLD_TERMS, key=len, reverse=True)
    replacements: list[tuple[str, str]] = []
    for index, term in enumerate(terms):
        escaped_term = html.escape(term)
        token = f"@@AUTO_BOLD_{index}@@"
        escaped = escaped.replace(escaped_term, token)
        replacements.append((token, f"<strong>{escaped_term}</strong>"))
    for token, value in replacements:
        escaped = escaped.replace(token, value)
    for index, value in enumerate(protected):
        escaped = escaped.replace(f"@@STRONG_{index}@@", value)
    return escaped


def format_report_title(text: str, report_date: str | None = None) -> str:
    date = report_date
    match = re.fullmatch(r"Morning Investment Briefing - (\d{4}-\d{2}-\d{2})", text)
    if match:
        date = match.group(1)
    if not date:
        return format_inline(text)
    return f"KO 데일리 브리핑 ({html.escape(short_date(date))})"


def short_date(date: str) -> str:
    match = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", date)
    if not match:
        return date
    return f"{match.group(1)[2:]}.{match.group(2)}.{match.group(3)}"


def metrics_meta(report_date: str) -> str:
    return (
        '<p class="metrics-meta">'
        f"{html.escape(report_date)} 08:00 KST 수집 기준입니다. "
        "표시값은 각 시장의 직전 거래일 마감 지표입니다."
        "</p>"
    )


def format_source_badges(escaped: str) -> str:
    replacements: list[tuple[str, str]] = []
    for index, (label, initial, source_class, title) in enumerate(
        sorted(SOURCE_BADGES, key=lambda item: len(item[0]), reverse=True)
    ):
        escaped_label = html.escape(label)
        token = f"@@SOURCE_BADGE_{index}@@"
        badge = (
            f'<span class="source-badge source-{source_class}" '
            f'title="{html.escape(title)}">{html.escape(initial)}</span>'
        )
        escaped = escaped.replace(escaped_label, token)
        replacements.append((token, badge))
    for token, badge in replacements:
        escaped = escaped.replace(token, badge)
    return escaped


def render_table(rows: list[list[str]]) -> list[str]:
    sorted_rows = sort_table_rows(rows)
    class_name = table_class(sorted_rows[0])
    is_portfolio = "portfolio-table" in class_name
    table_html = [f'<table class="{class_name}"><tbody>']
    for row_count, raw_cells in enumerate(sorted_rows):
        tag = "th" if row_count == 0 else "td"
        rendered_cells = []
        for index, raw_cell in enumerate(raw_cells):
            classes = cell_class(raw_cell)
            if "spark" in classes.split():
                cell = render_sparkline(raw_cell, sparkline_tone(raw_cells))
            else:
                cell = format_inline(raw_cell, source_badges=is_portfolio and row_count > 0)
            cell = wrap_tone_cell(cell, classes)
            rendered_cells.append(f"<{tag}{class_attr(table_cell_class(classes))}>{cell}</{tag}>")
        table_html.append("<tr>" + "".join(rendered_cells) + "</tr>")
    table_html.append("</tbody></table>")

    if not is_portfolio:
        return table_html
    return [
        '<section class="portfolio-panel">',
        source_legend(),
        *table_html,
        impact_legend(),
        "</section>",
    ]


def sort_table_rows(rows: list[list[str]]) -> list[list[str]]:
    if not rows or "metrics-table" not in table_class(rows[0]):
        return rows
    order = {name: index for index, name in enumerate(METRIC_ORDER)}
    header, data_rows = rows[0], rows[1:]
    return [header, *sorted(data_rows, key=lambda row: order.get(row[0], len(order)))]


def source_legend() -> str:
    badges = [
        ("N", "naver", "Naver Search"),
        ("D", "dart", "DART"),
        ("y", "yfinance", "yfinance"),
        ("C", "cnbc", "CNBC"),
    ]
    items = "".join(
        f'<span><span class="source-badge source-{source_class}">{initial}</span>{label}</span>'
        for initial, source_class, label in badges
    )
    return f'<div class="source-legend" aria-label="뉴스 출처 범례">{items}</div>'


def table_cell_class(classes: str) -> str:
    return " ".join(
        class_name for class_name in classes.split()
        if class_name not in {"tone-up", "tone-down", "tone-neutral"}
    )


def sparkline_tone(row: list[str]) -> str:
    for cell in row:
        stripped = cell.strip()
        if stripped.startswith("+"):
            return "up"
        if stripped.startswith("-"):
            return "down"
    return "up"


def render_sparkline(text: str, tone: str | None = None) -> str:
    values = [SPARK_VALUES[char] for char in text if char in SPARK_VALUES]
    if not values:
        return format_inline(text)

    width = 116
    height = 46
    pad_x = 7
    pad_y = 7
    usable_w = width - (pad_x * 2)
    usable_h = height - (pad_y * 2)
    max_value = max(values)
    min_value = min(values)
    span = max(max_value - min_value, 1)
    step = usable_w / max(len(values) - 1, 1)
    points = []
    for index, value in enumerate(values):
        x = pad_x + (step * index)
        normalized = (value - min_value) / span
        y = pad_y + usable_h - (normalized * usable_h)
        points.append((x, y))

    path = " ".join(
        ("M" if index == 0 else "L") + f"{x:.1f} {y:.1f}"
        for index, (x, y) in enumerate(points)
    )
    fill_points = (
        f"{points[0][0]:.1f},{height - pad_y:.1f} "
        + " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
        + f" {points[-1][0]:.1f},{height - pad_y:.1f}"
    )
    tone = tone or ("up" if values[-1] >= values[0] else "down")
    last_x, last_y = points[-1]
    return (
        f'<svg class="sparkline sparkline-{tone}" viewBox="0 0 {width} {height}" '
        'role="img" aria-label="7일 추이">'
        f'<line class="sparkline-baseline" x1="{pad_x}" y1="{height - pad_y}" '
        f'x2="{width - pad_x}" y2="{height - pad_y}"></line>'
        f'<polygon class="sparkline-fill" points="{fill_points}"></polygon>'
        f'<path class="sparkline-path" d="{path}"></path>'
        f'<circle class="sparkline-dot" cx="{last_x:.1f}" cy="{last_y:.1f}" r="4"></circle>'
        "</svg>"
    )


def wrap_tone_cell(cell: str, classes: str) -> str:
    for tone_class in ("tone-up", "tone-down", "tone-neutral"):
        if tone_class in classes.split():
            return f'<span class="{tone_class}">{cell}</span>'
    return cell


def impact_legend() -> str:
    return (
        '<div class="impact-legend" aria-label="영향도 기준">'
        '<span><strong>긍정</strong> 가격/공시/뉴스 흐름이 보유 종목에 우호적</span>'
        '<span><strong>중립</strong> 방향성이 제한적이거나 확인 필요</span>'
        '<span><strong>부정</strong> 가격 약세나 리스크 뉴스가 우세</span>'
        "</div>"
    )


def table_class(header_cells: list[str]) -> str:
    header = "|".join(header_cells)
    if "지표" in header and "종가 7일" in header:
        return "data-table metrics-table"
    if "종목" in header and "영향도" in header:
        return "data-table portfolio-table"
    if "주요 헤드라인" in header:
        return "data-table news-table"
    return "data-table"


def cell_class(text: str) -> str:
    classes: list[str] = []
    if re.search(r"[▁▂▃▄▅▆▇█]{3,}", text):
        classes.append("spark")
    if text.startswith("+") or re.search(r"\+\d", text):
        classes.append("value-up")
    elif text.startswith("-") or re.search(r"-\d", text):
        classes.append("value-down")
    if text == "긍정":
        classes.append("tone-up")
    elif text == "부정":
        classes.append("tone-down")
    elif text.startswith("중립"):
        classes.append("tone-neutral")
    return " ".join(classes)


def class_attr(class_name: str) -> str:
    return f' class="{class_name}"' if class_name else ""


def page(title: str, body: str, header: str = "") -> str:
    header_html = f"\n      {header}" if header else ""
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #070b12;
      --paper: #0f1623;
      --panel: #111c2d;
      --panel-soft: #162235;
      --text: #e6edf6;
      --muted: #94a3b8;
      --line: #253246;
      --line-strong: #34445c;
      --accent: #4fd1c5;
      --accent-strong: #9debdc;
      --gold: #d6b46a;
      --hot: #38bdf8;
      --up: #4ade80;
      --down: #fb7185;
    }}
    * {{
      box-sizing: border-box;
    }}
    body {{
      margin: 0;
      background:
        linear-gradient(rgba(148, 163, 184, 0.035) 1px, transparent 1px),
        linear-gradient(90deg, rgba(148, 163, 184, 0.03) 1px, transparent 1px),
        radial-gradient(circle at 18% -8%, rgba(56, 189, 248, 0.20), transparent 34%),
        radial-gradient(circle at 86% 12%, rgba(214, 180, 106, 0.12), transparent 28%),
        linear-gradient(180deg, #0b1220 0, var(--bg) 360px);
      background-size: 36px 36px, 36px 36px, auto, auto, auto;
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.55;
    }}
    main {{
      max-width: 1240px;
      margin: 0 auto;
      padding: 30px 22px 72px;
    }}
    article {{
      position: relative;
      overflow: hidden;
      background:
        linear-gradient(180deg, rgba(15, 22, 35, 0.96), rgba(10, 15, 24, 0.98)),
        var(--paper);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 42px;
      box-shadow: 0 34px 110px rgba(0, 0, 0, 0.48);
    }}
    article::before {{
      content: "";
      position: absolute;
      inset: 0;
      pointer-events: none;
      background:
        linear-gradient(90deg, rgba(79, 209, 197, 0.08), transparent 26%),
        radial-gradient(circle at 90% 0%, rgba(79, 209, 197, 0.12), transparent 30%);
      mask-image: linear-gradient(180deg, #000 0, transparent 340px);
    }}
    h1 {{
      position: relative;
      overflow: hidden;
      margin: 8px 0 28px;
      min-height: 172px;
      padding: 56px 34px 30px;
      border: 1px solid var(--line-strong);
      border-left: 7px solid var(--gold);
      border-radius: 14px;
      background:
        linear-gradient(135deg, rgba(20, 32, 51, 0.96), rgba(8, 13, 22, 0.98)),
        repeating-linear-gradient(90deg, transparent 0, transparent 22px, rgba(79, 209, 197, 0.05) 23px);
      color: #f8fafc;
      font-size: clamp(38px, 6vw, 68px);
      line-height: 1.04;
      letter-spacing: 0;
      text-shadow: 0 12px 36px rgba(0, 0, 0, 0.46);
    }}
    h1::before {{
      content: "KSS MARKET INTELLIGENCE";
      position: absolute;
      top: 24px;
      left: 34px;
      color: var(--gold);
      font-size: 12px;
      font-weight: 800;
      letter-spacing: 0.18em;
    }}
    h1::after {{
      content: "";
      position: absolute;
      right: 26px;
      bottom: 24px;
      width: min(42%, 360px);
      height: 72px;
      opacity: 0.8;
      background:
        linear-gradient(180deg, transparent 0 54%, rgba(79, 209, 197, 0.28) 55% 58%, transparent 59%),
        repeating-linear-gradient(90deg, rgba(79, 209, 197, 0.0) 0 14px, rgba(79, 209, 197, 0.55) 15px 22px);
      clip-path: polygon(0 72%, 8% 60%, 16% 68%, 26% 42%, 38% 58%, 48% 28%, 58% 50%, 70% 22%, 82% 36%, 100% 8%, 100% 100%, 0 100%);
    }}
    h2 {{
      display: flex;
      align-items: center;
      gap: 10px;
      margin: 42px 0 16px;
      padding: 12px 14px;
      border: 1px solid var(--line);
      border-left: 4px solid var(--accent);
      border-radius: 10px;
      background: linear-gradient(90deg, rgba(79, 209, 197, 0.13), rgba(17, 28, 45, 0.54));
      color: #f8fafc;
      font-size: 21px;
      letter-spacing: 0;
    }}
    h2::before {{
      content: "";
      width: 9px;
      height: 9px;
      border-radius: 999px;
      background: var(--accent);
      box-shadow: 0 0 18px rgba(79, 209, 197, 0.8);
      flex: 0 0 auto;
    }}
    h3 {{
      margin: 24px 0 8px;
      font-size: 17px;
      letter-spacing: 0;
    }}
    p, li {{
      font-size: 15px;
      color: #dce7f3;
    }}
    p {{
      margin: 0 0 14px;
    }}
    ul {{
      margin: 0 0 14px;
      padding-left: 22px;
    }}
    .data-table {{
      width: 100%;
      border-collapse: collapse;
      margin: 14px 0 24px;
      font-size: 14px;
      overflow: hidden;
      border-radius: 10px;
      background: rgba(8, 13, 22, 0.58);
      box-shadow: 0 0 0 1px var(--line), 0 18px 46px rgba(0, 0, 0, 0.30);
    }}
    .data-table th, .data-table td {{
      border: 1px solid var(--line);
      padding: 10px 12px;
      text-align: left;
      vertical-align: top;
    }}
    .data-table th {{
      background: linear-gradient(180deg, #18304a, #132238);
      color: var(--accent-strong);
      font-size: 13px;
      font-weight: 750;
    }}
    .data-table tr:nth-child(even) td {{
      background: rgba(255, 255, 255, 0.025);
    }}
    .data-table tr:hover td {{
      background: rgba(79, 209, 197, 0.055);
    }}
    .metrics-table {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 16px;
      border-collapse: separate;
      box-shadow: none;
      overflow: visible;
    }}
    .metrics-meta {{
      margin: -6px 0 14px;
      color: var(--muted);
      font-size: 13px;
    }}
    .metrics-table tr,
    .metrics-table td {{
      display: block;
    }}
    .metrics-table tbody {{
      display: contents;
    }}
    .metrics-table tr:first-child {{
      display: none;
    }}
    .metrics-table tr {{
      position: relative;
      min-height: 158px;
      padding: 17px;
      border: 1px solid var(--line-strong);
      border-radius: 12px;
      background:
        linear-gradient(180deg, rgba(17, 28, 45, 0.92), rgba(9, 15, 24, 0.98)),
        radial-gradient(circle at 100% 0%, rgba(79, 209, 197, 0.16), transparent 30%);
      box-shadow: 0 18px 42px rgba(0, 0, 0, 0.34);
    }}
    .metrics-table tr::before {{
      content: "";
      position: absolute;
      inset: 0;
      border-radius: inherit;
      pointer-events: none;
      background: linear-gradient(90deg, rgba(214, 180, 106, 0.42), transparent 32%);
      height: 3px;
    }}
    .metrics-table td {{
      border: 0;
      padding: 0;
    }}
    .metrics-table td:nth-child(1) {{
      color: var(--muted);
      font-size: 12px;
      font-weight: 750;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }}
    .metrics-table td:nth-child(3) {{
      margin-top: 10px;
      color: #f8fafc;
      font-size: 28px;
      font-weight: 800;
      line-height: 1.15;
    }}
    .metrics-table td:nth-child(2) {{
      margin-top: 3px;
      color: var(--muted);
      font-size: 12px;
    }}
    .metrics-table td:nth-child(2)::before {{
      content: "직전 ";
    }}
    .metrics-table td:nth-child(4),
    .metrics-table td:nth-child(5) {{
      display: inline-block;
      margin-top: 10px;
      margin-right: 6px;
      padding: 2px 8px;
      border-radius: 999px;
      background: rgba(148, 163, 184, 0.14);
      font-size: 12px;
      font-weight: 750;
    }}
    .metrics-table td:nth-child(6) {{
      margin-top: 12px;
    }}
    .portfolio-table td:nth-child(1) {{
      font-weight: 700;
      white-space: nowrap;
    }}
    .portfolio-table td:nth-child(3),
    .portfolio-table td:nth-child(4),
    .portfolio-table td:nth-child(5) {{
      white-space: nowrap;
      font-variant-numeric: tabular-nums;
    }}
    .portfolio-panel {{
      position: relative;
      margin: 14px 0 24px;
      overflow-x: auto;
      padding: 12px 0 8px;
      border-radius: 12px;
      background: linear-gradient(180deg, rgba(17, 28, 45, 0.36), rgba(8, 13, 22, 0.22));
    }}
    .portfolio-panel .portfolio-table {{
      min-width: 1060px;
      margin-top: 8px;
      margin-bottom: 0;
    }}
    .portfolio-table th:first-child,
    .portfolio-table td:first-child {{
      position: sticky;
      left: 0;
      z-index: 2;
      background: #101a2a;
    }}
    .portfolio-table th:first-child {{
      z-index: 3;
      background: #18304a;
    }}
    .portfolio-table th,
    .portfolio-table td {{
      vertical-align: middle;
    }}
    .source-legend {{
      display: flex;
      flex-wrap: wrap;
      justify-content: flex-end;
      gap: 6px 10px;
      margin: 0 0 8px;
      padding-right: 2px;
      color: var(--muted);
      font-size: 12px;
    }}
    .source-legend span {{
      display: inline-flex;
      align-items: center;
      gap: 4px;
    }}
    .impact-legend {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 8px;
      margin-top: 10px;
      color: var(--muted);
      font-size: 12px;
    }}
    .impact-legend span {{
      padding: 8px 10px;
      border: 1px solid var(--line);
      border-radius: 10px;
      background: rgba(17, 28, 45, 0.72);
    }}
    .impact-legend strong {{
      margin-right: 4px;
      color: var(--text);
    }}
    .source-badge {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 18px;
      height: 18px;
      margin: 0 3px;
      border-radius: 999px;
      color: #ffffff;
      font-size: 11px;
      font-weight: 800;
      line-height: 1;
      vertical-align: -2px;
    }}
    .source-badge:first-child {{
      margin-left: 0;
    }}
    .source-naver {{
      background: #03c75a;
    }}
    .source-dart {{
      background: #2563eb;
    }}
    .source-yfinance {{
      background: #7c3aed;
    }}
    .source-cnbc {{
      background: #0f766e;
    }}
    .news-table td:first-child {{
      width: 150px;
      font-weight: 700;
      color: var(--accent-strong);
    }}
    .spark {{
      white-space: nowrap;
      min-width: 132px;
    }}
    .sparkline {{
      display: block;
      width: 122px;
      height: 48px;
      overflow: visible;
    }}
    .sparkline-baseline {{
      stroke: rgba(148, 163, 184, 0.42);
      stroke-width: 1;
      stroke-dasharray: 5 6;
    }}
    .sparkline-fill {{
      opacity: 0.18;
    }}
    .sparkline-path {{
      fill: none;
      stroke-width: 3;
      stroke-linecap: round;
      stroke-linejoin: round;
      filter: drop-shadow(0 0 8px currentColor);
    }}
    .sparkline-dot {{
      stroke: rgba(15, 22, 35, 0.9);
      stroke-width: 2;
      filter: drop-shadow(0 0 10px currentColor);
    }}
    .sparkline-up {{
      color: #38bdf8;
    }}
    .sparkline-up .sparkline-path,
    .sparkline-up .sparkline-dot {{
      stroke: currentColor;
      fill: currentColor;
    }}
    .sparkline-up .sparkline-fill {{
      fill: #38bdf8;
    }}
    .sparkline-down {{
      color: #fb4562;
    }}
    .sparkline-down .sparkline-path,
    .sparkline-down .sparkline-dot {{
      stroke: currentColor;
      fill: currentColor;
    }}
    .sparkline-down .sparkline-fill {{
      fill: #fb4562;
    }}
    .value-up {{
      color: var(--up);
    }}
    .value-down {{
      color: var(--down);
    }}
    .tone-up,
    .tone-down,
    .tone-neutral {{
      display: inline-block;
      min-width: 58px;
      padding: 3px 10px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 750;
      text-align: center;
      white-space: nowrap;
    }}
    .tone-up {{
      background: rgba(74, 222, 128, 0.13);
      color: var(--up);
    }}
    .tone-down {{
      background: rgba(251, 113, 133, 0.13);
      color: var(--down);
    }}
    .tone-neutral {{
      background: rgba(148, 163, 184, 0.14);
      color: #cbd5e1;
    }}
    .meta {{
      margin-bottom: 16px;
      color: var(--muted);
      font-size: 13px;
    }}
    .brief-header {{
      position: sticky;
      top: 12px;
      z-index: 20;
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 8px 12px;
      margin-bottom: 14px;
      padding: 10px 12px;
      border: 1px solid var(--line);
      border-radius: 12px;
      background: rgba(17, 28, 45, 0.86);
      backdrop-filter: blur(14px);
      color: var(--muted);
      font-size: 13px;
    }}
    .brief-header::before {{
      content: "";
      width: 8px;
      height: 8px;
      border-radius: 999px;
      background: var(--accent);
    }}
    .brief-title {{
      margin: 0;
      color: var(--text);
      font-size: 13px;
      font-weight: 700;
    }}
    .brief-links {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .brief-links a {{
      display: inline-flex;
      align-items: center;
      min-height: 24px;
      padding: 2px 8px;
      border-radius: 999px;
      background: rgba(79, 209, 197, 0.12);
      color: var(--accent);
      font-size: 13px;
      text-decoration: none;
    }}
    .brief-links a:hover {{
      background: rgba(79, 209, 197, 0.22);
      text-decoration: none;
    }}
    .back-link {{
      display: inline-flex;
      align-items: center;
      min-height: 24px;
      padding: 2px 8px;
      border-radius: 999px;
      background: var(--panel-soft);
      color: var(--accent);
      font-size: 13px;
      font-weight: 700;
      text-decoration: none;
      box-shadow: inset 0 0 0 1px var(--line-strong);
    }}
    .back-link:hover {{
      text-decoration: underline;
    }}
    @media (max-width: 900px) {{
      .metrics-table {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }}
    }}
    @media (max-width: 640px) {{
      main {{
        padding: 16px 10px 36px;
      }}
      article {{
        padding: 20px 14px;
      }}
      h1 {{
        padding: 18px;
        font-size: 25px;
      }}
      .metrics-table {{
        grid-template-columns: 1fr;
      }}
      .data-table:not(.metrics-table) {{
        display: block;
        overflow-x: auto;
      }}
      .impact-legend {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body>
  <main>
    <article>
      {header_html.lstrip()}
      {body}
    </article>
  </main>
</body>
</html>
"""


def index_header(
    current_date: str,
    archive_dates: list[str],
    *,
    in_archive: bool = False,
) -> str:
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args(argv)

    report_path = Path(args.report)
    if not report_path.exists():
        print(f"report not found: {report_path}", file=sys.stderr)
        return 1

    markdown = report_path.read_text(encoding="utf-8")
    html_body = markdown_to_html(markdown, report_date=args.date)
    reports_dir = DOCS_DIR / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    dated_path = reports_dir / f"{args.date}.html"
    index_path = DOCS_DIR / "index.html"

    dates = archive_dates(reports_dir)
    if args.date not in dates:
        dates.append(args.date)
        dates.sort()
    sorted_dates = sorted(dates, reverse=True)
    page_title = f"KO 데일리 브리핑 ({short_date(args.date)})"
    dated_rendered = page(
        page_title,
        html_body,
        header=index_header(args.date, sorted_dates, in_archive=True),
    )
    dated_path.write_text(dated_rendered, encoding="utf-8")
    latest_rendered = page(
        page_title,
        html_body,
        header=index_header(args.date, sorted_dates),
    )
    index_path.write_text(latest_rendered, encoding="utf-8")

    print(f"wrote {index_path}")
    print(f"wrote {dated_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
