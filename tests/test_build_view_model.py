from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src import build_view_model


class BuildViewModelTests(unittest.TestCase):
    def test_build_view_model_preserves_prices_flows_news_and_disclosures(self) -> None:
        source = {
            "date": "2026-06-05",
            "as_of": "2026-06-05T08:00:00+09:00",
            "timezone": "Asia/Seoul",
            "portfolio": [{
                "market": "KR",
                "name": "삼성전자",
                "symbol": "005930",
                "tier": 2,
                "factors": ["semiconductor"],
            }],
            "market_data": {
                "market_indicators": [{
                    "name": "KOSPI",
                    "symbol": "^KS11",
                    "source": "yfinance",
                    "close": 8160.59,
                    "previous_close": 8639.41,
                    "change": -478.82,
                    "change_pct": -5.54,
                    "recent_closes": [8228.7, 8185.29, 8160.59],
                }],
                "kr_quotes": [{
                    "symbol": "005930",
                    "name": "삼성전자",
                    "source": "naver_finance",
                    "price": 329000,
                    "recent_closes": [307000, 351500, 329000],
                }],
                "krx_quotes": [{
                    "symbol": "005930",
                    "source": "pykrx_fallback",
                    "as_of_date": "20260605",
                    "change_pct": -6.4,
                    "volume": 123,
                }],
                "investor_flows": {
                    "markets": [],
                    "holdings": [{
                        "source": "pykrx_fallback",
                        "symbol": "005930",
                        "name": "삼성전자",
                        "unit": "KRW",
                        "institution": -479,
                        "foreign": -1405,
                        "individual": 1794,
                        "seven_day_total": {
                            "available": True,
                            "trading_days": 7,
                            "institution": -1200,
                            "foreign": -3000,
                            "individual": 4200,
                        },
                    }],
                },
            },
            "news": [{
                "source": "naver_search_news",
                "symbol": "005930",
                "name": "삼성전자",
                "title": "외국인 매도",
            }],
            "disclosures": [{
                "source": "dart",
                "symbol": "005930",
                "name": "삼성전자",
                "report_name": "임원ㆍ주요주주특정증권등소유상황보고서",
            }],
            "data_quality": [],
        }

        view_model = build_view_model.build_view_model(source)
        holding = view_model["holdings"][0]

        self.assertEqual(view_model["schema"], "kss-view-model.v1")
        self.assertEqual(view_model["market_status"]["label"], "주의")
        self.assertEqual(view_model["market_indicators"][0]["price"]["close_7d_ago"], 8228.7)
        self.assertEqual(view_model["market_indicators"][0]["display_order"], 0)
        self.assertIn("시장 약세", view_model["market_indicators"][0]["risk_tags"])
        self.assertEqual(holding["price"]["latest_close"], 329000)
        self.assertEqual(holding["price"]["close_7d_ago"], 307000)
        self.assertEqual(holding["price"]["change"], -22500)
        self.assertEqual(holding["sector"], "semiconductor")
        self.assertEqual(holding["impact"]["label"], "부정")
        self.assertEqual(holding["primary_issue"], "가격 약세와 외인 매도")
        self.assertEqual(holding["data_status"]["price"], "ok")
        self.assertEqual(holding["flow"]["latest"]["foreign"], -1405)
        self.assertTrue(holding["flow"]["seven_day_total"]["available"])
        self.assertEqual(holding["flow"]["seven_day_total"]["foreign"], -3000)
        self.assertEqual(holding["news"][0]["title"], "외국인 매도")
        self.assertEqual(holding["disclosures"][0]["source"], "dart")

    def test_main_writes_view_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_path = tmp_path / "source.json"
            output_path = tmp_path / "view_model.json"
            source_path.write_text(json.dumps({
                "date": "2026-06-05",
                "portfolio": [],
                "market_data": {},
                "news": [],
                "disclosures": [],
                "data_quality": [],
            }), encoding="utf-8")

            exit_code = build_view_model.main([
                "--date", "2026-06-05",
                "--source", str(source_path),
                "--output", str(output_path),
            ])

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.exists())


if __name__ == "__main__":
    unittest.main()
