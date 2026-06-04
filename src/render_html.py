from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs"


def markdown_to_html(markdown: str) -> str:
    lines = markdown.splitlines()
    output: list[str] = []
    in_list = False
    in_table = False
    table_row_count = 0

    def close_blocks() -> None:
        nonlocal in_list, in_table, table_row_count
        if in_list:
            output.append("</ul>")
            in_list = False
        if in_table:
            output.append("</tbody></table>")
            in_table = False
            table_row_count = 0

    for line in lines:
        stripped = line.strip()
        if not stripped:
            close_blocks()
            continue

        if stripped.startswith("|") and stripped.endswith("|"):
            raw_cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            cells = [format_inline(cell) for cell in raw_cells]
            if all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in raw_cells):
                continue
            if not in_table:
                close_blocks()
                output.append(f'<table class="{table_class(raw_cells)}"><tbody>')
                in_table = True
            tag = "th" if table_row_count == 0 else "td"
            output.append("<tr>" + "".join(
                f"<{tag}{class_attr(cell_class(raw_cells[index]))}>{cell}</{tag}>"
                for index, cell in enumerate(cells)
            ) + "</tr>")
            table_row_count += 1
            continue

        close_blocks()

        if stripped.startswith("# "):
            output.append(f"<h1>{format_inline(stripped[2:])}</h1>")
        elif stripped.startswith("## "):
            output.append(f"<h2>{format_inline(stripped[3:])}</h2>")
        elif stripped.startswith("### "):
            output.append(f"<h3>{format_inline(stripped[4:])}</h3>")
        elif stripped.startswith("- "):
            if not in_list:
                output.append("<ul>")
                in_list = True
            output.append(f"<li>{format_inline(stripped[2:])}</li>")
        elif re.match(r"^\d+\. ", stripped):
            output.append(f"<p>{format_inline(stripped)}</p>")
        else:
            output.append(f"<p>{format_inline(stripped)}</p>")

    close_blocks()
    return "\n".join(output)


def format_inline(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    return escaped


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
      color-scheme: light;
      --bg: #eef2f6;
      --paper: #ffffff;
      --text: #1f2933;
      --muted: #667085;
      --line: #d7dde7;
      --accent: #0f766e;
      --accent-strong: #0b4f4a;
      --up: #087443;
      --down: #b42318;
    }}
    * {{
      box-sizing: border-box;
    }}
    body {{
      margin: 0;
      background: linear-gradient(180deg, #dce7ee 0, var(--bg) 280px);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.55;
    }}
    main {{
      max-width: 1120px;
      margin: 0 auto;
      padding: 28px 20px 64px;
    }}
    article {{
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 34px;
      box-shadow: 0 18px 50px rgba(31, 41, 51, 0.08);
    }}
    h1 {{
      margin: 8px 0 28px;
      padding: 22px 24px;
      border: 1px solid #cfe2df;
      border-left: 6px solid var(--accent);
      border-radius: 8px;
      background: linear-gradient(135deg, #f7fbfa, #edf5f3);
      color: #111827;
      font-size: 34px;
      line-height: 1.18;
      letter-spacing: 0;
    }}
    h2 {{
      margin: 34px 0 14px;
      padding-top: 18px;
      border-top: 1px solid #e2e8f0;
      font-size: 21px;
      letter-spacing: 0;
    }}
    h3 {{
      margin: 24px 0 8px;
      font-size: 17px;
      letter-spacing: 0;
    }}
    p, li {{
      font-size: 15px;
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
      border-radius: 8px;
      box-shadow: 0 0 0 1px var(--line);
    }}
    .data-table th, .data-table td {{
      border: 1px solid #e0e6ef;
      padding: 10px 12px;
      text-align: left;
      vertical-align: top;
    }}
    .data-table th {{
      background: #edf5f4;
      color: #174a46;
      font-size: 13px;
      font-weight: 750;
    }}
    .data-table tr:nth-child(even) td {{
      background: #fbfcfe;
    }}
    .metrics-table {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      border-collapse: separate;
      box-shadow: none;
      overflow: visible;
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
      min-height: 132px;
      padding: 14px;
      border: 1px solid #d8e5e2;
      border-radius: 8px;
      background: linear-gradient(180deg, #ffffff, #f7faf9);
      box-shadow: 0 8px 22px rgba(31, 41, 51, 0.06);
    }}
    .metrics-table td {{
      border: 0;
      padding: 0;
    }}
    .metrics-table td:nth-child(1) {{
      color: var(--muted);
      font-size: 12px;
      font-weight: 750;
    }}
    .metrics-table td:nth-child(3) {{
      margin-top: 8px;
      color: #111827;
      font-size: 24px;
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
      background: #f2f4f7;
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
    .news-table td:first-child {{
      width: 150px;
      font-weight: 700;
      color: var(--accent-strong);
    }}
    .spark {{
      color: var(--accent);
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 18px;
      letter-spacing: 1px;
      white-space: nowrap;
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
      border-radius: 999px;
      font-size: 12px;
      font-weight: 750;
      text-align: center;
      white-space: nowrap;
    }}
    .tone-up {{
      background: #e8f6ef;
      color: var(--up);
    }}
    .tone-down {{
      background: #fff0ed;
      color: var(--down);
    }}
    .tone-neutral {{
      background: #f2f4f7;
      color: #475467;
    }}
    .meta {{
      margin-bottom: 16px;
      color: var(--muted);
      font-size: 13px;
    }}
    .brief-header {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 8px 12px;
      margin-bottom: 14px;
      padding: 10px 12px;
      border: 1px solid #d9e6e3;
      border-radius: 8px;
      background: #f7fbfa;
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
      background: #e9f5f2;
      color: var(--accent);
      font-size: 13px;
      text-decoration: none;
    }}
    .brief-links a:hover {{
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


def index_header(current_date: str, archive_dates: list[str]) -> str:
    links = "\n".join(
        f'<a href="reports/{html.escape(date)}.html">{html.escape(date)}</a>'
        for date in archive_dates
    )
    return f"""<section class="brief-header">
        <p class="brief-title">Latest: {html.escape(current_date)} KST</p>
        <span>Archives</span>
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
    html_body = markdown_to_html(markdown)
    reports_dir = DOCS_DIR / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    dated_path = reports_dir / f"{args.date}.html"
    index_path = DOCS_DIR / "index.html"

    dated_rendered = page(f"Morning Investment Briefing - {args.date}", html_body)
    dated_path.write_text(dated_rendered, encoding="utf-8")

    dates = archive_dates(reports_dir)
    if args.date not in dates:
        dates.append(args.date)
        dates.sort()
    latest_rendered = page(
        f"Morning Investment Briefing - {args.date}",
        html_body,
        header=index_header(args.date, sorted(dates, reverse=True)),
    )
    index_path.write_text(latest_rendered, encoding="utf-8")

    print(f"wrote {index_path}")
    print(f"wrote {dated_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
