from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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
        self.assertIn("pykrx_quotes", snapshot["market_data"])
        self.assertIn("kr_indices", snapshot["market_data"])
        self.assertGreater(len(snapshot["portfolio"]), 0)
        self.assertIn(
            {"source": "dart", "status": "skipped", "reason": "offline mode"},
            snapshot["data_quality"],
        )
        self.assertIn(
            {"source": "pykrx", "status": "skipped", "reason": "offline mode"},
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

    def test_pykrx_offline_is_skipped(self) -> None:
        quotes, indices, quality = collect.collect_pykrx([], "2026-06-02", offline=True)

        self.assertEqual(quotes, [])
        self.assertEqual(indices, [])
        self.assertEqual(quality, [{"source": "pykrx", "status": "skipped", "reason": "offline mode"}])

    def test_pykrx_without_krx_credentials_is_skipped(self) -> None:
        with mock.patch.dict("os.environ", {}, clear=True):
            quotes, indices, quality = collect.collect_pykrx([], "2026-06-02", offline=False)

        self.assertEqual(quotes, [])
        self.assertEqual(indices, [])
        self.assertEqual(quality, [{"source": "pykrx", "status": "skipped", "reason": "KRX_ID or KRX_PW not set"}])

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
