from __future__ import annotations

import unittest
import tempfile
from pathlib import Path

from src.render_html import archive_dates, index_header, markdown_to_html


class RenderHtmlTests(unittest.TestCase):
    def test_basic_markdown_rendering(self) -> None:
        html = markdown_to_html("# Title\n\n## Section\n\n- Item\n\n| A | B |\n| --- | --- |\n| 1 | 2 |")

        self.assertIn("<h1>Title</h1>", html)
        self.assertIn("<h2>Section</h2>", html)
        self.assertIn("<li>Item</li>", html)
        self.assertIn("<table>", html)
        self.assertIn("<th>A</th>", html)

    def test_index_header_links_to_archives(self) -> None:
        html = index_header("2026-06-04", ["2026-06-04", "2026-06-02"])

        self.assertIn("Latest Briefing", html)
        self.assertIn('href="reports/2026-06-04.html"', html)
        self.assertIn('href="reports/2026-06-02.html"', html)

    def test_archive_dates_only_returns_dated_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            reports_dir = Path(tmp)
            (reports_dir / "2026-06-04.html").write_text("", encoding="utf-8")
            (reports_dir / "not-a-report.html").write_text("", encoding="utf-8")

            self.assertEqual(archive_dates(reports_dir), ["2026-06-04"])


if __name__ == "__main__":
    unittest.main()
