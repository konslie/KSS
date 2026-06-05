from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "data" / "reports"


def build_analysis_context(view_model: dict[str, Any]) -> dict[str, Any]:
    holdings = view_model.get("holdings", [])
    return {
        "schema": "kss-analysis-context.v1",
        "date": view_model.get("date"),
        "as_of": view_model.get("as_of"),
        "timezone": view_model.get("timezone"),
        "executive_summary_inputs": executive_summary_inputs(view_model),
        "market_context": market_context(view_model),
        "sector_contexts": sector_contexts(holdings),
        "holding_contexts": [holding_context(holding) for holding in holdings],
        "news_clusters": news_clusters(view_model.get("news", [])),
        "disclosure_clusters": disclosure_clusters(view_model.get("disclosures", [])),
        "data_quality_summary": data_quality_summary(view_model),
    }


def executive_summary_inputs(view_model: dict[str, Any]) -> dict[str, Any]:
    return {
        "market_status": view_model.get("market_status", {}),
        "coverage": view_model.get("coverage", {}),
        "top_market_moves": top_market_moves(view_model.get("market_indicators", [])),
        "top_holding_moves": top_holding_moves(view_model.get("holdings", [])),
        "data_quality_count": len(view_model.get("data_quality", [])),
    }


def market_context(view_model: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": view_model.get("market_status", {}),
        "indicators": [
            {
                "name": row.get("name"),
                "symbol": row.get("symbol"),
                "latest_close": row.get("price", {}).get("latest_close"),
                "change": row.get("price", {}).get("change"),
                "change_pct": row.get("price", {}).get("change_pct"),
                "trend": row.get("price", {}).get("trend"),
                "risk_tags": row.get("risk_tags", []),
                "short_comment": row.get("short_comment"),
                "source": row.get("source"),
            }
            for row in view_model.get("market_indicators", [])
        ],
        "flows": view_model.get("market_flows", []),
    }


def sector_contexts(holdings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for holding in holdings:
        groups[holding.get("sector") or "portfolio"].append(holding)
    return [
        {
            "sector": sector,
            "holdings": [holding.get("symbol") for holding in rows],
            "price_summary": summarize_prices(rows),
            "flow_summary": summarize_flows(rows),
            "news_summary": summarize_counts(rows, "news"),
            "disclosure_summary": summarize_counts(rows, "disclosures"),
            "risks": sector_risks(rows),
        }
        for sector, rows in sorted(groups.items())
    ]


def holding_context(holding: dict[str, Any]) -> dict[str, Any]:
    price = holding.get("price", {})
    flow = holding.get("flow", {})
    latest_flow = flow.get("latest", {})
    seven_flow = flow.get("seven_day_total", {})
    return {
        "name": holding.get("name"),
        "symbol": holding.get("symbol"),
        "market": holding.get("market"),
        "sector": holding.get("sector"),
        "priority": holding.get("priority"),
        "impact": holding.get("impact", {}),
        "primary_issue": holding.get("primary_issue"),
        "price_summary": {
            "latest_close": price.get("latest_close"),
            "previous_close": price.get("previous_close"),
            "change": price.get("change"),
            "change_pct": price.get("change_pct"),
            "trend": price.get("trend"),
            "recent_closes": price.get("recent_closes", []),
            "recent_dates": price.get("recent_dates", []),
        },
        "flow_summary": {
            "latest": latest_flow,
            "seven_day_total": seven_flow,
        },
        "news_summary": item_summary(holding.get("news", []), "news"),
        "disclosure_summary": item_summary(holding.get("disclosures", []), "disclosure"),
        "data_status": holding.get("data_status", {}),
    }


def news_clusters(news: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return clusters_by_source(news, "news")


def disclosure_clusters(disclosures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return clusters_by_source(disclosures, "disclosure")


def clusters_by_source(rows: list[dict[str, Any]], item_type: str) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[row.get("source") or "unknown"].append(row)
    return [
        {
            "source": source,
            "count": len(items),
            "items": item_summary(items[:10], item_type),
        }
        for source, items in sorted(groups.items())
    ]


def data_quality_summary(view_model: dict[str, Any]) -> dict[str, Any]:
    rows = view_model.get("data_quality", [])
    missing_prices = [
        holding.get("symbol")
        for holding in view_model.get("holdings", [])
        if holding.get("data_status", {}).get("price") == "missing"
    ]
    return {
        "items": rows,
        "count": len(rows),
        "missing_price_symbols": missing_prices,
        "coverage": view_model.get("coverage", {}),
    }


def top_market_moves(indicators: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = sorted(
        indicators,
        key=lambda row: abs(number(row.get("price", {}).get("change_pct")) or 0),
        reverse=True,
    )
    return [
        {
            "name": row.get("name"),
            "change_pct": row.get("price", {}).get("change_pct"),
            "short_comment": row.get("short_comment"),
            "risk_tags": row.get("risk_tags", []),
        }
        for row in rows[:5]
    ]


def top_holding_moves(holdings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = sorted(
        holdings,
        key=lambda row: abs(number(row.get("price", {}).get("change_pct")) or 0),
        reverse=True,
    )
    return [
        {
            "name": row.get("name"),
            "symbol": row.get("symbol"),
            "change_pct": row.get("price", {}).get("change_pct"),
            "impact": row.get("impact", {}).get("label"),
            "primary_issue": row.get("primary_issue"),
        }
        for row in rows[:8]
    ]


def summarize_prices(rows: list[dict[str, Any]]) -> dict[str, Any]:
    changes = [number(row.get("price", {}).get("change_pct")) for row in rows]
    clean = [value for value in changes if value is not None]
    return {
        "count": len(rows),
        "positive_count": sum(1 for value in clean if value > 0),
        "negative_count": sum(1 for value in clean if value < 0),
        "average_change_pct": round(sum(clean) / len(clean), 2) if clean else None,
    }


def summarize_flows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    foreign = [number(row.get("flow", {}).get("latest", {}).get("foreign")) for row in rows]
    institution = [number(row.get("flow", {}).get("latest", {}).get("institution")) for row in rows]
    return {
        "foreign_total": sum(value for value in foreign if value is not None),
        "institution_total": sum(value for value in institution if value is not None),
    }


def summarize_counts(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    return {
        "count": sum(len(row.get(key, [])) for row in rows),
        "holding_count": sum(1 for row in rows if row.get(key)),
    }


def sector_risks(rows: list[dict[str, Any]]) -> list[str]:
    risks = []
    if any((number(row.get("price", {}).get("change_pct")) or 0) <= -3 for row in rows):
        risks.append("가격 급락 종목 포함")
    if any(row.get("data_status", {}).get("price") == "missing" for row in rows):
        risks.append("최신 가격 누락")
    if any(row.get("impact", {}).get("label") in {"부정", "중립~부정"} for row in rows):
        risks.append("부정적 영향도 포함")
    return risks


def item_summary(rows: list[dict[str, Any]], item_type: str) -> list[dict[str, Any]]:
    title_keys = ["title", "report_name", "headline"]
    output = []
    for row in rows:
        title = next((row.get(key) for key in title_keys if row.get(key)), "")
        output.append({
            "type": item_type,
            "source": row.get("source"),
            "symbol": row.get("symbol"),
            "name": row.get("name"),
            "title": title,
            "url": row.get("url"),
            "published_at": row.get("published_at") or row.get("date"),
        })
    return output


def number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument(
        "--view-model",
        default=None,
        help="Path to view_model.json. Defaults to data/reports/DATE/view_model.json.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Path to write analysis_context.json. Defaults to data/reports/DATE/analysis_context.json.",
    )
    args = parser.parse_args(argv)

    view_model_path = Path(args.view_model) if args.view_model else REPORTS_DIR / args.date / "view_model.json"
    output_path = Path(args.output) if args.output else REPORTS_DIR / args.date / "analysis_context.json"
    if not view_model_path.exists():
        print(f"view model not found: {view_model_path}", file=sys.stderr)
        return 1

    view_model = json.loads(view_model_path.read_text(encoding="utf-8"))
    analysis_context = build_analysis_context(view_model)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(analysis_context, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
