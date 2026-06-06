from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src import build_analysis_context


class BuildAnalysisContextTests(unittest.TestCase):
    def test_build_analysis_context_groups_market_sector_and_holding_context(self) -> None:
        view_model = {
            "date": "2026-06-05",
            "as_of": "2026-06-05T08:00:00+09:00",
            "timezone": "Asia/Seoul",
            "market_status": {"label": "주의", "score": 1},
            "coverage": {"holding_count": 1},
            "market_indicators": [{
                "name": "KOSPI",
                "symbol": "^KS11",
                "source": "pykrx",
                "risk_tags": ["시장 약세"],
                "short_comment": "약세",
                "price": {
                    "latest_close": 8160.59,
                    "change": -478.82,
                    "change_pct": -5.54,
                    "trend": "down",
                },
            }],
            "market_flows": [],
            "holdings": [{
                "name": "삼성전자",
                "symbol": "005930",
                "market": "KR",
                "sector": "semiconductor",
                "priority": 10,
                "impact": {"label": "부정", "score": -2},
                "primary_issue": "가격 약세와 외인 매도",
                "price": {
                    "latest_close": 329000,
                    "previous_close": 351500,
                    "change": -22500,
                    "change_pct": -6.4,
                    "trend": "down",
                    "recent_closes": [307000, 351500, 329000],
                },
                "flow": {
                    "latest": {"foreign": -1405, "institution": -479},
                    "seven_day_total": {"available": True, "foreign": -3000},
                },
                "news": [{"source": "naver", "symbol": "005930", "title": "외국인 매도"}],
                "disclosures": [{"source": "dart", "symbol": "005930", "report_name": "주요사항보고서"}],
                "data_status": {"price": "ok", "flow": "ok", "news": "ok", "disclosures": "ok"},
            }],
            "news": [{"source": "naver", "symbol": "005930", "title": "외국인 매도"}],
            "disclosures": [{"source": "dart", "symbol": "005930", "report_name": "주요사항보고서"}],
            "data_quality": [],
        }

        context = build_analysis_context.build_analysis_context(view_model)

        self.assertEqual(context["schema"], "kss-analysis-context.v1")
        self.assertEqual(context["executive_summary_inputs"]["market_status"]["label"], "주의")
        self.assertEqual(context["market_context"]["indicators"][0]["risk_tags"], ["시장 약세"])
        self.assertEqual(context["sector_contexts"][0]["sector"], "semiconductor")
        self.assertIn("가격 방향과 외인/기관 수급이 같은 종목", context["sector_contexts"][0]["interpretation_cues"][0])
        self.assertEqual(context["holding_contexts"][0]["primary_issue"], "가격 약세와 외인 매도")
        self.assertEqual(context["holding_contexts"][0]["interpretation_cues"]["price_flow_signal"], "confirmed")
        self.assertIn("외국인 매도", context["holding_contexts"][0]["interpretation_cues"]["briefing_focus"])
        self.assertEqual(context["news_clusters"][0]["count"], 1)
        self.assertEqual(context["disclosure_clusters"][0]["count"], 1)

    def test_main_writes_analysis_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            view_model_path = tmp_path / "view_model.json"
            output_path = tmp_path / "analysis_context.json"
            view_model_path.write_text(json.dumps({
                "date": "2026-06-05",
                "market_indicators": [],
                "holdings": [],
                "news": [],
                "disclosures": [],
                "data_quality": [],
            }), encoding="utf-8")

            exit_code = build_analysis_context.main([
                "--date", "2026-06-05",
                "--view-model", str(view_model_path),
                "--output", str(output_path),
            ])

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.exists())


if __name__ == "__main__":
    unittest.main()
