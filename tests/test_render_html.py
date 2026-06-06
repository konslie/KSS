from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src import render_html
from src.render_html import archive_dates, app_shell, index_header, markdown_to_report


class RenderHtmlTests(unittest.TestCase):
    def test_basic_markdown_becomes_report_data(self) -> None:
        report = markdown_to_report("# Title\n\n## Section\n\n- Item\n\n| A | B |\n| --- | --- |\n| 1 | 2 |")

        self.assertEqual(report["schema"], "kss-report.v1")
        self.assertEqual(report["elements"][0], {"type": "heading", "level": 1, "text": "Title"})
        self.assertEqual(report["elements"][1], {"type": "heading", "level": 2, "text": "Section"})
        self.assertEqual(report["elements"][2], {"type": "list", "items": ["Item"], "autoBold": False})
        self.assertEqual(report["elements"][3]["type"], "table")
        self.assertEqual(report["elements"][3]["header"], ["A", "B"])

    def test_report_title_and_metrics_meta(self) -> None:
        report = markdown_to_report(
            "# Morning Investment Briefing - 2026-06-04\n\n"
            "## 주요 거시지표\n\n"
            "| 지표 | 직전 거래일 종가 | 종가 | 등락폭 | 등락률 | 종가 7일 |\n"
            "| --- | --- | --- | --- | --- | --- |\n"
            "| KOSPI | 1 | 2 | +1 | +1% | ▁▂▃ |",
            report_date="2026-06-04",
        )

        self.assertEqual(report["title"], "KO_데일리브리핑(26.06.04)")
        self.assertEqual(report["elements"][0]["text"], "KO_데일리브리핑(26.06.04)")
        self.assertIn("2026-06-04 08:00 KST 수집 기준", report["elements"][2]["text"])

    def test_metrics_table_uses_requested_order(self) -> None:
        report = markdown_to_report(
            "| 지표 | 직전 거래일 종가 | 종가 | 등락폭 | 등락률 | 종가 7일 |\n"
            "| --- | --- | --- | --- | --- | --- |\n"
            "| USD/KRW | 1 | 2 | +1 | +1% | ▁▂▃ |\n"
            "| Nasdaq | 1 | 2 | +1 | +1% | ▁▂▃ |\n"
            "| KOSPI | 1 | 2 | +1 | +1% | ▁▂▃ |\n"
            "| 필라델피아반도체지수 | 1 | 2 | +1 | +1% | ▁▂▃ |\n"
            "| VIX | 1 | 2 | +1 | +1% | ▁▂▃ |\n"
        )

        rows = report["elements"][0]["rows"]
        names = [row[0] for row in rows]
        self.assertLess(names.index("KOSPI"), names.index("Nasdaq"))
        self.assertLess(names.index("Nasdaq"), names.index("VIX"))
        self.assertLess(names.index("USD/KRW"), names.index("필라델피아반도체지수"))
        self.assertEqual(report["elements"][0]["className"], "metrics-table")

    def test_portfolio_table_is_marked_for_frontend_badges_and_legend(self) -> None:
        report = markdown_to_report(
            "| 종목 | 영향도 | 종가 | 등락폭 | 등락률 | 7일 | 근거 |\n"
            "| --- | --- | --- | --- | --- | --- | --- |\n"
            "| Nvidia | 부정 | $214.75 | -$8.07 | -3.62% | ▇▆▅ | CNBC와 yfinance 뉴스에 AI 투자 둔화 우려가 포함됐다. |\n"
            "| 현대차2우B | 긍정 | 266,000원 | +14,273원 | +5.67% | ▁▂▃ | DART에 영업잠정실적 공시가 포함됐다. |"
        )

        table = report["elements"][0]
        self.assertEqual(table["className"], "portfolio-table")
        self.assertEqual(table["header"], ["종목", "영향도", "가격", "기관", "외인", "7일", "근거"])
        self.assertEqual(table["rows"][0][2], "$214.75\n-$8.07 (-3.62%)")
        self.assertEqual(table["rows"][0][3], "")

    def test_auto_bold_flag_is_limited_to_summary_and_sector_briefings(self) -> None:
        report = markdown_to_report(
            "## 1. Executive Summary\n\n"
            "- 오늘의 한줄 요약: Nvidia 약세와 DART 공시를 확인했다.\n\n"
            "## 8. 오늘의 관찰 포인트\n\n"
            "Nvidia는 여기서 자동 강조하지 않는다."
        )

        summary_list = report["elements"][1]
        observation_paragraph = report["elements"][3]
        self.assertTrue(summary_list["autoBold"])
        self.assertFalse(observation_paragraph["autoBold"])

    def test_app_shell_links_assets_and_report_json(self) -> None:
        html = app_shell(
            title="KO 데일리 브리핑 (26.06.04)",
            report_json="reports/2026-06-04.json",
            current_date="2026-06-04",
            archive_dates=["2026-06-04", "2026-06-03"],
            report_data={
                "title": "KO 데일리 브리핑 (26.06.04)",
                "report": {"elements": []},
                "view_model": {"holdings": []},
            },
        )

        self.assertIn('href="assets/report.css?v=20260604-layout2"', html)
        self.assertIn('src="assets/report.js?v=20260604-layout2"', html)
        self.assertIn('data-report-json="reports/2026-06-04.json"', html)
        self.assertIn('id="report-data"', html)
        self.assertIn("2026-06-03", html)

    def test_index_header_links_to_archives(self) -> None:
        html = index_header(
            "2026-06-04",
            ["2026-06-04", "2026-06-03", "2026-06-02", "2026-06-01", "2026-05-29", "2026-05-28"],
        )

        self.assertIn("Latest: 2026-06-04 KST", html)
        self.assertIn("최근 5일", html)
        self.assertIn('href="reports/2026-06-04.html"', html)
        self.assertIn('href="reports/2026-06-02.html"', html)
        self.assertNotIn('href="reports/2026-05-28.html"', html)

    def test_archive_header_has_back_link(self) -> None:
        html = index_header("2026-06-04", ["2026-06-04"], in_archive=True)

        self.assertIn('href="../index.html"', html)
        self.assertIn('href="2026-06-04.html"', html)

    def test_archive_dates_only_returns_dated_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            reports_dir = Path(tmp)
            (reports_dir / "2026-06-04.html").write_text("", encoding="utf-8")
            (reports_dir / "not-a-report.html").write_text("", encoding="utf-8")
            (reports_dir / "2026-06-04.json").write_text("", encoding="utf-8")

            self.assertEqual(archive_dates(reports_dir), ["2026-06-04"])

    def test_main_writes_shell_assets_and_report_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            docs_dir = Path(tmp) / "docs"
            report_path = Path(tmp) / "final.md"
            report_path.write_text("# Morning Investment Briefing - 2026-06-04\n", encoding="utf-8")
            with mock.patch.object(render_html, "DOCS_DIR", docs_dir):
                with mock.patch.object(render_html, "ASSETS_DIR", docs_dir / "assets"):
                    exit_code = render_html.main(["--date", "2026-06-04", "--report", str(report_path)])

            self.assertEqual(exit_code, 0)
            self.assertTrue((docs_dir / "index.html").exists())
            self.assertTrue((docs_dir / "reports" / "2026-06-04.html").exists())
            json_path = docs_dir / "reports" / "2026-06-04.json"
            self.assertTrue(json_path.exists())
            self.assertTrue((docs_dir / "assets" / "report.css").exists())
            self.assertTrue((docs_dir / "assets" / "report.js").exists())
            self.assertIn('id="report-data"', (docs_dir / "index.html").read_text(encoding="utf-8"))
            data = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(data["title"], "KO_데일리브리핑(26.06.04)")
            self.assertEqual(data["schema"], "kss-page.v1")
            self.assertIn("report", data)
            self.assertIn("view_model", data)


if __name__ == "__main__":
    unittest.main()
