"""Command-line entry point for KSS."""

from __future__ import annotations

import argparse
import json

from kss.analysis import analyze_stock, result_to_dict
from kss.mock_data import MOCK_PROVIDER


def main() -> None:
    parser = argparse.ArgumentParser(description="Run KSS valuation with the local mock provider.")
    parser.add_argument("query", help="Korean stock name or ticker, for example 삼성전자 or 005930")
    args = parser.parse_args()

    result = analyze_stock(args.query, MOCK_PROVIDER)
    print(json.dumps(result_to_dict(result), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
