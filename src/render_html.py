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
            cells = [format_inline(cell.strip()) for cell in stripped.strip("|").split("|")]
            if all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in stripped.strip("|").split("|")):
                continue
            if not in_table:
                close_blocks()
                output.append("<table><tbody>")
                in_table = True
            tag = "th" if table_row_count == 0 else "td"
            output.append("<tr>" + "".join(f"<{tag}>{cell}</{tag}>" for cell in cells) + "</tr>")
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
      --bg: #f7f8fa;
      --paper: #ffffff;
      --text: #1f2933;
      --muted: #667085;
      --line: #d8dee8;
      --accent: #0f766e;
    }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.55;
    }}
    main {{
      max-width: 980px;
      margin: 0 auto;
      padding: 40px 20px 64px;
    }}
    article {{
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 32px;
    }}
    h1 {{
      margin: 0 0 24px;
      font-size: 32px;
      letter-spacing: 0;
    }}
    h2 {{
      margin: 32px 0 12px;
      padding-top: 20px;
      border-top: 1px solid var(--line);
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
    ul {{
      padding-left: 22px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin: 12px 0 20px;
      font-size: 14px;
    }}
    th, td {{
      border: 1px solid var(--line);
      padding: 10px 12px;
      text-align: left;
      vertical-align: top;
    }}
    th {{
      background: #eef6f5;
      color: #134e4a;
    }}
    .meta {{
      margin-bottom: 16px;
      color: var(--muted);
      font-size: 13px;
    }}
    .brief-header {{
      margin-bottom: 24px;
      padding-bottom: 20px;
      border-bottom: 1px solid var(--line);
    }}
    .brief-title {{
      margin: 0 0 8px;
      font-size: 18px;
      font-weight: 700;
    }}
    .brief-links {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 12px;
    }}
    .brief-links a {{
      color: var(--accent);
      font-size: 13px;
      text-decoration: none;
    }}
    .brief-links a:hover {{
      text-decoration: underline;
    }}
    @media (max-width: 640px) {{
      main {{
        padding: 16px 10px 36px;
      }}
      article {{
        padding: 20px 14px;
      }}
      h1 {{
        font-size: 24px;
      }}
      table {{
        display: block;
        overflow-x: auto;
      }}
    }}
  </style>
</head>
<body>
  <main>
    <article>
      <div class="meta">Generated by Morning Investment Briefing</div>{header_html}
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
        <p class="brief-title">Latest Briefing</p>
        <div class="meta">Current report: {html.escape(current_date)} KST</div>
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
