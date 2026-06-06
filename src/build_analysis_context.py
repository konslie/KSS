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
            "interpretation_cues": sector_interpretation_cues(rows),
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
        "interpretation_cues": holding_interpretation_cues(holding),
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
        risks.append("최근 종가 누락")
    if any(row.get("impact", {}).get("label") in {"부정", "중립~부정"} for row in rows):
        risks.append("부정적 영향도 포함")
    return risks


def sector_interpretation_cues(rows: list[dict[str, Any]]) -> list[str]:
    cues = []
    aligned = []
    diverged = []
    for row in rows:
        signal = price_flow_signal(row)
        if signal == "confirmed":
            aligned.append(row.get("name") or row.get("symbol"))
        elif signal == "diverged":
            diverged.append(row.get("name") or row.get("symbol"))
    if aligned:
        cues.append(f"가격 방향과 외인/기관 수급이 같은 종목: {', '.join(aligned[:4])}")
    if diverged:
        cues.append(f"가격 방향과 외인/기관 수급이 엇갈린 종목: {', '.join(diverged[:4])}")
    news_titles = [
        title
        for row in rows
        for title in key_titles(row.get("news", []), "news")
    ]
    disclosure_titles = [
        title
        for row in rows
        for title in key_titles(row.get("disclosures", []), "disclosure")
    ]
    if news_titles:
        cues.append(f"뉴스 해석 초점: {' / '.join(news_titles[:3])}")
    if disclosure_titles:
        cues.append(f"공시 해석 초점: {' / '.join(disclosure_titles[:3])}")
    return cues


def holding_interpretation_cues(holding: dict[str, Any]) -> dict[str, Any]:
    signal = price_flow_signal(holding)
    issue_titles = key_titles(holding.get("news", []), "news") + key_titles(holding.get("disclosures", []), "disclosure")
    return {
        "price_flow_signal": signal,
        "price_flow_note": price_flow_note(holding, signal),
        "issue_titles": issue_titles[:5],
        "issue_directness": issue_directness(holding, issue_titles[:5]),
        "briefing_focus": briefing_focus(holding, signal, issue_titles),
    }


def price_flow_signal(holding: dict[str, Any]) -> str:
    pct = number(holding.get("price", {}).get("change_pct"))
    latest = holding.get("flow", {}).get("latest", {})
    foreign = number(latest.get("foreign"))
    institution = number(latest.get("institution"))
    if pct is None or (foreign is None and institution is None):
        return "insufficient_data"
    flow_total = sum(value for value in (foreign, institution) if value is not None)
    if flow_total == 0 or abs(pct) < 1:
        return "mixed_or_weak"
    if (pct > 0 and flow_total > 0) or (pct < 0 and flow_total < 0):
        return "confirmed"
    return "diverged"


def price_flow_note(holding: dict[str, Any], signal: str) -> str:
    name = holding.get("name") or holding.get("symbol") or "해당 종목"
    if signal == "confirmed":
        return f"{name}은 가격 방향과 외인/기관 합산 수급이 같은 방향이라 당일 움직임이 수급으로 확인되는지 봐야 한다."
    if signal == "diverged":
        return f"{name}은 가격 방향과 외인/기관 합산 수급이 엇갈려 단기 매도/매수 주체와 뉴스 재료의 우선순위를 분리해서 봐야 한다."
    if signal == "mixed_or_weak":
        return f"{name}은 가격 또는 수급 신호가 약해 뉴스·공시의 실제 관련성을 먼저 확인해야 한다."
    return f"{name}은 가격 또는 수급 데이터가 부족해 확인 가능한 뉴스·공시만 해석 근거로 써야 한다."


def briefing_focus(holding: dict[str, Any], signal: str, issue_titles: list[str]) -> str:
    primary_issue = holding.get("primary_issue") or "특이 신호"
    issue_phrase = f"{primary_issue}{object_particle(primary_issue)}"
    if issue_titles:
        directness = issue_directness(holding, issue_titles[:1])[0]
        caution = "" if directness == "direct" else " 직접 관련성 확인 필요를 표시하고,"
        return f"{issue_phrase} 숫자 반복으로 끝내지 말고, '{issue_titles[0]}' 이슈의{caution} 가격·수급 신호와의 관계를 설명한다."
    if signal in {"confirmed", "diverged"}:
        return f"{issue_phrase} 가격 변화보다 수급 확인/괴리 관점에서 설명한다."
    return f"{primary_issue}은(는) 추가 재료가 제한적임을 명확히 표시한다."


def issue_directness(holding: dict[str, Any], titles: list[str]) -> list[str]:
    name = str(holding.get("name") or "").lower()
    symbol = str(holding.get("symbol") or "").lower()
    output = []
    for title in titles:
        lowered = title.lower()
        if (name and name in lowered) or (symbol and symbol in lowered):
            output.append("direct")
        else:
            output.append("needs_relevance_check")
    return output


def object_particle(text: str) -> str:
    if not text:
        return "을"
    last = text[-1]
    code = ord(last)
    if 0xAC00 <= code <= 0xD7A3 and (code - 0xAC00) % 28 == 0:
        return "를"
    return "을"


def key_titles(rows: list[dict[str, Any]], item_type: str) -> list[str]:
    title_keys = ["title", "report_name", "headline"] if item_type == "news" else ["report_name", "title", "headline"]
    titles = []
    for row in rows:
        title = next((row.get(key) for key in title_keys if row.get(key)), "")
        if title:
            titles.append(str(title).strip())
    return titles


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
