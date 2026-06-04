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
        self.assertIn('<table class="data-table">', html)
        self.assertIn("<th>A</th>", html)

    def test_report_title_and_metrics_meta(self) -> None:
        html = markdown_to_html(
            "# Morning Investment Briefing - 2026-06-04\n\n"
            "## 주요 거시지표\n\n"
            "| 지표 | 직전 거래일 종가 | 종가 | 등락폭 | 등락률 | 종가 7일 |\n"
            "| --- | --- | --- | --- | --- | --- |\n"
            "| KOSPI | 1 | 2 | +1 | +1% | ▁▂▃ |",
            report_date="2026-06-04",
        )

        self.assertIn("<h1>KO 데일리 브리핑 (26.06.04)</h1>", html)
        self.assertIn("2026-06-04 08:00 KST 수집 기준", html)

    def test_metrics_table_uses_requested_order(self) -> None:
        html = markdown_to_html(
            "| 지표 | 직전 거래일 종가 | 종가 | 등락폭 | 등락률 | 종가 7일 |\n"
            "| --- | --- | --- | --- | --- | --- |\n"
            "| USD/KRW | 1 | 2 | +1 | +1% | ▁▂▃ |\n"
            "| Nasdaq | 1 | 2 | +1 | +1% | ▁▂▃ |\n"
            "| KOSPI | 1 | 2 | +1 | +1% | ▁▂▃ |\n"
            "| 필라델피아반도체지수 | 1 | 2 | +1 | +1% | ▁▂▃ |\n"
            "| VIX | 1 | 2 | +1 | +1% | ▁▂▃ |\n"
        )

        self.assertLess(html.index("<td>KOSPI</td>"), html.index("<td>Nasdaq</td>"))
        self.assertLess(html.index("<td>Nasdaq</td>"), html.index("<td>VIX</td>"))
        self.assertLess(html.index("<td>USD/KRW</td>"), html.index("<td>필라델피아반도체지수</td>"))
        self.assertIn('class="sparkline sparkline-up"', html)
        self.assertIn('class="sparkline-path"', html)
        self.assertIn('class="sparkline-baseline"', html)

    def test_portfolio_table_renders_source_badges_and_legend(self) -> None:
        html = markdown_to_html(
            "| 종목 | 영향도 | 근거 |\n"
            "| --- | --- | --- |\n"
            "| Nvidia | 부정 | CNBC와 yfinance 뉴스에 AI 투자 둔화 우려가 포함됐다. |\n"
            "| 현대차2우B | 긍정 | DART에 영업잠정실적 공시가 포함됐다. |\n"
            "| 하나금융지주 | 긍정 | Naver Search 뉴스에 은행주 강세가 포함됐다. |"
        )

        self.assertIn('class="source-legend"', html)
        self.assertIn('class="source-badge source-naver"', html)
        self.assertIn('class="source-badge source-dart"', html)
        self.assertIn('class="source-badge source-yfinance"', html)
        self.assertIn('class="source-badge source-cnbc"', html)
        self.assertNotIn('source-<span', html)
        self.assertIn('class="impact-legend"', html)
        self.assertIn('<td><span class="tone-down">부정</span></td>', html)
        self.assertNotIn('<td class="tone-down">부정</td>', html)

    def test_source_badges_are_limited_to_portfolio_table(self) -> None:
        html = markdown_to_html(
            "## 1. Executive Summary\n\n"
            "- DART 공시와 yfinance 뉴스가 있었다.\n\n"
            "## 2. 포트폴리오 영향도\n\n"
            "| 종목 | 영향도 | 근거 |\n"
            "| --- | --- | --- |\n"
            "| Nvidia | 부정 | CNBC와 yfinance 뉴스에 AI 투자 둔화 우려가 포함됐다. |"
        )

        self.assertIn("<li><strong>DART</strong> 공시와 <strong>yfinance</strong> 뉴스가 있었다.</li>", html)
        self.assertIn('class="source-badge source-yfinance"', html)

    def test_key_terms_are_bolded_in_summary_and_sector_briefings(self) -> None:
        html = markdown_to_html(
            "## 1. Executive Summary\n\n"
            "- 오늘의 한줄 요약: Nvidia 약세와 DART 공시를 확인했다.\n\n"
            "## 3. 금융주 브리핑\n\n"
            "하나금융지주와 DB손해보험은 상승했다.\n\n"
            "## 8. 오늘의 관찰 포인트\n\n"
            "Nvidia는 여기서 자동 강조하지 않는다."
        )

        self.assertIn("<strong>오늘의 한줄 요약</strong>", html)
        self.assertIn("<strong>Nvidia</strong>", html)
        self.assertIn("<strong>DART</strong>", html)
        self.assertIn("<strong>하나금융지주</strong>", html)
        self.assertIn("<strong>DB손해보험</strong>", html)
        self.assertIn("<p>Nvidia는 여기서 자동 강조하지 않는다.</p>", html)

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

            self.assertEqual(archive_dates(reports_dir), ["2026-06-04"])


if __name__ == "__main__":
    unittest.main()
