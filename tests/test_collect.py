from __future__ import annotations

import json
import math
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd

from src import collect


class CollectTests(unittest.TestCase):
    def test_offline_snapshot_has_expected_shape(self) -> None:
        snapshot = collect.build_snapshot("2026-06-02", offline=True)

        self.assertEqual(snapshot["date"], "2026-06-02")
        self.assertIn("portfolio", snapshot)
        self.assertIn("market_data", snapshot)
        self.assertIn("disclosures", snapshot)
        self.assertIn("data_quality", snapshot)
        self.assertIn("market_indicators", snapshot["market_data"])
        self.assertIn("krx_quotes", snapshot["market_data"])
        self.assertIn("kr_indices", snapshot["market_data"])
        self.assertIn("investor_flows", snapshot["market_data"])
        self.assertGreater(len(snapshot["portfolio"]), 0)
        self.assertIn(
            {"source": "dart", "status": "skipped", "reason": "offline mode"},
            snapshot["data_quality"],
        )
        self.assertIn(
            {"source": "krx_open_api", "status": "skipped", "reason": "offline mode"},
            snapshot["data_quality"],
        )
        self.assertIn(
            {"source": "krx_investor_flows", "status": "skipped", "reason": "offline mode"},
            snapshot["data_quality"],
        )
        self.assertIn(
            {"source": "yfinance_indicators", "status": "skipped", "reason": "offline mode"},
            snapshot["data_quality"],
        )

    def test_dart_without_api_key_is_skipped(self) -> None:
        with mock.patch.dict("os.environ", {}, clear=True):
            disclosures, quality = collect.collect_dart([], "2026-06-02", offline=False)

        self.assertEqual(disclosures, [])
        self.assertEqual(quality, [{"source": "dart", "status": "skipped", "reason": "DART_API_KEY not set"}])

    def test_krx_open_api_reference_without_auth_key_is_skipped(self) -> None:
        with mock.patch.dict("os.environ", {}, clear=True):
            quotes, indices, quality = collect.collect_krx_open_api_reference([], "2026-06-02", offline=False)

        self.assertEqual(quotes, [])
        self.assertEqual(indices, [])
        self.assertEqual(quality, [{"source": "krx_open_api", "status": "skipped", "reason": "KRX_AUTH_KEY not set"}])

    def test_investor_flows_without_krx_auth_key_is_skipped(self) -> None:
        with mock.patch.dict("os.environ", {}, clear=True):
            flows, quality = collect.collect_investor_flows([], "2026-06-02", offline=False)

        self.assertEqual(flows, {"markets": [], "holdings": []})
        self.assertEqual(quality, [{
            "source": "krx_investor_flows",
            "status": "skipped",
            "reason": "KRX_AUTH_KEY not set",
        }, {
            "source": "pykrx_fallback",
            "status": "skipped",
            "reason": "KRX_ID or KRX_PW not set",
        }])

    def test_investor_flows_without_open_api_path_is_skipped(self) -> None:
        with mock.patch.dict("os.environ", {"KRX_AUTH_KEY": "token"}, clear=True):
            flows, quality = collect.collect_investor_flows([], "2026-06-02", offline=False)

        self.assertEqual(flows, {"markets": [], "holdings": []})
        self.assertEqual(quality, [{
            "source": "krx_investor_flows",
            "status": "skipped",
            "reason": "KRX investor flow Open API path not configured",
        }, {
            "source": "pykrx_fallback",
            "status": "skipped",
            "reason": "KRX_ID or KRX_PW not set",
        }])

    def test_investor_flows_use_krx_open_api_paths(self) -> None:
        holdings = [
            {"market": "KR", "name": "삼성전자", "symbol": "005930"},
            {"market": "US", "name": "Nvidia", "symbol": "NVDA"},
        ]

        def fake_request(api_path: str, params: dict[str, str], timeout: int = 20) -> dict[str, object]:
            self.assertIn(api_path, {"sto/investor_market", "sto/investor_holding"})
            if api_path == "sto/investor_market":
                self.assertIn(params["mktId"], {"STK", "KSQ"})
            if api_path == "sto/investor_holding":
                self.assertEqual(params["isuCd"], "005930")
            return {
                "output": {
                    "result": [
                        {"INVST_TP_NM": "개인", "NET_BUY_TRDVAL": "-1000"},
                        {"INVST_TP_NM": "기관합계", "NET_BUY_TRDVAL": "500"},
                        {"INVST_TP_NM": "외국인합계", "NET_BUY_TRDVAL": "1500"},
                    ]
                }
            }

        with mock.patch.dict("os.environ", {
            "KRX_AUTH_KEY": "token",
            "KRX_INVESTOR_MARKET_API_PATH": "sto/investor_market",
            "KRX_INVESTOR_HOLDING_API_PATH": "sto/investor_holding",
        }, clear=True):
            with mock.patch.object(collect, "request_krx_open_api", side_effect=fake_request):
                flows, quality = collect.collect_investor_flows(holdings, "2026-06-02", offline=False)

        self.assertEqual(quality, [])
        self.assertEqual([row["market"] for row in flows["markets"]], ["KOSPI", "KOSDAQ"])
        self.assertEqual([row["symbol"] for row in flows["holdings"]], ["005930"])
        self.assertEqual(flows["markets"][0]["buy_leader"], "외국인")
        self.assertEqual(flows["markets"][0]["sell_leader"], "개인")
        self.assertEqual(flows["holdings"][0]["individual"], -1000)

    def test_krx_open_api_urls_try_documented_path_before_json_suffix(self) -> None:
        urls = collect.krx_open_api_urls(
            "https://data-dbg.krx.co.kr/svc/sample/apis",
            "sto/stk_bydd_trd",
            {"basDd": "20200414"},
        )

        self.assertEqual(urls, [
            "https://data-dbg.krx.co.kr/svc/sample/apis/sto/stk_bydd_trd?basDd=20200414",
            "https://data-dbg.krx.co.kr/svc/sample/apis/sto/stk_bydd_trd.json?basDd=20200414",
        ])

    def test_naver_news_query_uses_common_stock_name_for_preferred_stock(self) -> None:
        self.assertEqual(
            collect.naver_news_query({"name": "현대차2우B", "symbol": "005387"}),
            "현대차",
        )
        self.assertEqual(
            collect.naver_news_query({"name": "금호석유화학우", "symbol": "011785"}),
            "금호석유화학",
        )

    def test_naver_search_news_without_credentials_is_skipped(self) -> None:
        with mock.patch.dict("os.environ", {}, clear=True):
            rows, quality = collect.collect_naver_news([], offline=False)

        self.assertEqual(rows, [])
        self.assertEqual(quality, [{
            "source": "naver_search_news",
            "status": "skipped",
            "reason": "NAVER_CLIENT_ID or NAVER_CLIENT_SECRET not set",
        }])

    def test_normalize_yfinance_news(self) -> None:
        row = collect.normalize_yfinance_news("AAPL", {
            "title": "Apple news",
            "publisher": "Yahoo Finance",
            "link": "https://example.com/apple",
            "providerPublishTime": 1780550400,
        })

        self.assertIsNotNone(row)
        self.assertEqual(row["source"], "yfinance_news")
        self.assertEqual(row["symbol"], "AAPL")
        self.assertEqual(row["title"], "Apple news")
        self.assertEqual(row["url"], "https://example.com/apple")

    def test_fetch_yfinance_quote_ignores_invalid_latest_close(self) -> None:
        class FakeTicker:
            def history(self, period: str, interval: str, auto_adjust: bool) -> pd.DataFrame:
                return pd.DataFrame({
                    "Close": [16.42, 16.53, 15.875, math.nan],
                    "Volume": [15317500, 11900900, 3452975, 0],
                }, index=pd.to_datetime([
                    "2026-06-03",
                    "2026-06-04",
                    "2026-06-05",
                    "2026-06-08",
                ]))

        class FakeYFinance:
            @staticmethod
            def Ticker(symbol: str) -> FakeTicker:
                return FakeTicker()

        row, warning = collect.fetch_yfinance_quote(FakeYFinance, "CPNG")

        self.assertIsNotNone(row)
        self.assertEqual(row["close"], 15.875)
        self.assertEqual(row["previous_close"], 16.53)
        self.assertEqual(row["change"], -0.655)
        self.assertEqual(row["change_pct"], -3.96)
        self.assertEqual(row["as_of_date"], "2026-06-05")
        self.assertEqual(row["recent_closes"], [16.42, 16.53, 15.875])
        self.assertEqual(row["recent_dates"], ["2026-06-03", "2026-06-04", "2026-06-05"])
        self.assertEqual(warning["status"], "partial")

    def test_fetch_yfinance_quote_does_not_use_rows_after_report_date(self) -> None:
        class FakeTicker:
            def history(self, period: str, interval: str, auto_adjust: bool) -> pd.DataFrame:
                return pd.DataFrame({
                    "Close": [16.53, 15.875, 17.25],
                    "Volume": [11900900, 3452975, 9999999],
                }, index=pd.to_datetime([
                    "2026-06-04",
                    "2026-06-05",
                    "2026-06-08",
                ]))

        class FakeYFinance:
            @staticmethod
            def Ticker(symbol: str) -> FakeTicker:
                return FakeTicker()

        row, warning = collect.fetch_yfinance_quote(FakeYFinance, "CPNG", max_date="2026-06-07")

        self.assertIsNotNone(row)
        self.assertIsNone(warning)
        self.assertEqual(row["close"], 15.875)
        self.assertEqual(row["previous_close"], 16.53)
        self.assertEqual(row["as_of_date"], "2026-06-05")

    def test_naver_price_falls_back_to_latest_valid_yfinance_close(self) -> None:
        holdings = [{"market": "KR", "name": "삼성전자", "symbol": "005930"}]
        history = {
            "close": 70100,
            "previous_close": 69500,
            "change": 600,
            "change_pct": 0.86,
            "as_of_date": "2026-06-05",
            "recent_closes": [69000, 69500, 70100],
            "recent_dates": ["2026-06-03", "2026-06-04", "2026-06-05"],
        }
        fake_yfinance = types.SimpleNamespace()

        with mock.patch.dict(sys.modules, {"yfinance": fake_yfinance}):
            with mock.patch.object(collect, "fetch_url", return_value="<html></html>"):
                with mock.patch.object(collect, "fetch_yfinance_quote", return_value=(history, None)):
                    rows, quality = collect.collect_naver(holdings, offline=False)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["source"], "naver_finance_yfinance_fallback")
        self.assertEqual(rows[0]["price"], 70100)
        self.assertEqual(rows[0]["previous_close"], 69500)
        self.assertEqual(rows[0]["as_of_date"], "2026-06-05")
        self.assertEqual(rows[0]["recent_closes"], [69000, 69500, 70100])
        self.assertEqual(quality[0]["status"], "partial")

    def test_naver_backfill_uses_yfinance_close_at_or_before_report_date(self) -> None:
        holdings = [{"market": "KR", "name": "삼성전자", "symbol": "005930"}]
        page = '''
            <p class="no_today"><span class="blind">75,000</span></p>
            <p class="no_exday"><span class="blind">+2.00</span></p>
        '''
        history = {
            "close": 70100,
            "previous_close": 69500,
            "change": 600,
            "change_pct": 0.86,
            "as_of_date": "2026-06-05",
            "recent_closes": [69000, 69500, 70100],
            "recent_dates": ["2026-06-03", "2026-06-04", "2026-06-05"],
        }
        fake_yfinance = types.SimpleNamespace()
        fake_now = collect.dt.datetime(2026, 6, 8, 7, 0, tzinfo=collect.dt.timezone(collect.dt.timedelta(hours=9)))

        with mock.patch.dict(sys.modules, {"yfinance": fake_yfinance}):
            with mock.patch.object(collect, "now_kst", return_value=fake_now):
                with mock.patch.object(collect, "fetch_url", return_value=page):
                    with mock.patch.object(collect, "fetch_yfinance_quote", return_value=(history, None)):
                        rows, quality = collect.collect_naver(holdings, offline=False, run_date="2026-06-07")

        self.assertEqual(rows[0]["source"], "yfinance_backfill")
        self.assertEqual(rows[0]["price"], 70100)
        self.assertEqual(rows[0]["as_of_date"], "2026-06-05")
        self.assertEqual(quality[0]["reason"], "backfill run; used yfinance close at or before report date")

    def test_first_krx_rows_skips_holiday_rows_without_valid_close(self) -> None:
        responses = [{
            "output": {"result": [{"BAS_DD": "20260607", "TDD_CLSPRC": "-"}]},
        }, {
            "output": {"result": [{"BAS_DD": "20260605", "TDD_CLSPRC": "70,100"}]},
        }]

        with mock.patch.object(collect, "request_krx_open_api", side_effect=responses):
            rows, error = collect.first_krx_rows("sto/stk_bydd_trd", ["20260607", "20260605"], ("TDD_CLSPRC",))

        self.assertIsNone(error)
        self.assertEqual(rows[0]["BAS_DD"], "20260605")
        self.assertEqual(rows[0]["TDD_CLSPRC"], "70,100")

    def test_dart_uses_common_stock_fallback_for_preferred_stock(self) -> None:
        holdings = [{"market": "KR", "name": "현대차2우B", "symbol": "005387", "tier": 1}]
        payload = {"status": "013"}

        with mock.patch.dict("os.environ", {"DART_API_KEY": "token"}, clear=True):
            with mock.patch.object(collect, "get_dart_corp_map", return_value={"005380": "00164742"}):
                with mock.patch.object(collect, "fetch_url", return_value=json.dumps(payload)) as fetch:
                    disclosures, quality = collect.collect_dart(holdings, "2026-06-04", offline=False)

        self.assertEqual(disclosures, [])
        self.assertEqual(quality, [])
        self.assertIn("corp_code=00164742", fetch.call_args.args[0])

    def test_main_writes_source_and_news(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(collect, "INCOMING_DIR", Path(tmp)):
                exit_code = collect.main(["--date", "2026-06-02", "--offline"])

            self.assertEqual(exit_code, 0)
            source_path = Path(tmp) / "2026-06-02" / "source.json"
            news_path = Path(tmp) / "2026-06-02" / "news.md"
            self.assertTrue(source_path.exists())
            self.assertTrue(news_path.exists())
            data = json.loads(source_path.read_text(encoding="utf-8"))
            self.assertEqual(data["date"], "2026-06-02")


if __name__ == "__main__":
    unittest.main()
