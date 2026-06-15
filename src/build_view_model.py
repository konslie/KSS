from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
INCOMING_DIR = ROOT / "data" / "incoming"
REPORTS_DIR = ROOT / "data" / "reports"


def build_view_model(source: dict[str, Any]) -> dict[str, Any]:
    market_data = source.get("market_data", {})
    news = source.get("news", [])
    disclosures = source.get("disclosures", [])
    flows = market_data.get("investor_flows", {})
    indicator_rows = market_indicator_rows(market_data)
    holdings = [
        holding_model(holding, source, news, disclosures)
        for holding in source.get("portfolio", [])
    ]

    return {
        "schema": "kss-view-model.v1",
        "date": source.get("date"),
        "as_of": source.get("as_of"),
        "timezone": source.get("timezone"),
        "market_status": market_status_model({"market_indicators": indicator_rows}),
        "market_indicators": [
            market_indicator_model(row, index)
            for index, row in enumerate(indicator_rows)
        ],
        "holdings": holdings,
        "market_flows": [
            flow_model(row)
            for row in flows.get("markets", [])
        ],
        "news": news,
        "disclosures": disclosures,
        "data_quality": source.get("data_quality", []),
        "coverage": {
            "news_count": len(news),
            "disclosure_count": len(disclosures),
            "holding_count": len(source.get("portfolio", [])),
            "seven_day_flow_available": any(
                holding["flow"]["seven_day_total"].get("available")
                for holding in holdings
            ),
        },
    }


def market_indicator_rows(market_data: dict[str, Any]) -> list[dict[str, Any]]:
    kr_indices = market_data.get("kr_indices", [])
    return [
        merge_domestic_index_indicator(row, find_by_name(kr_indices, str(row.get("name") or "")))
        for row in market_data.get("market_indicators", [])
    ]


def merge_domestic_index_indicator(row: dict[str, Any], reference: dict[str, Any] | None) -> dict[str, Any]:
    name = str(row.get("name") or "")
    if name not in {"KOSPI", "KOSDAQ"} or not reference:
        return row
    reference_close = clean_number(reference.get("close"))
    reference_date = normalize_date_token(reference.get("as_of_date"))
    row_date = normalize_date_token(row.get("as_of_date"))
    if reference_close is None or (row_date and reference_date <= row_date):
        return row

    previous = clean_number(row.get("close")) or clean_number(row.get("previous_close"))
    change = reference_close - previous if previous is not None else clean_number(reference.get("change"))
    change_pct = (
        (change / previous) * 100
        if previous not in (None, 0) and change is not None
        else clean_number(reference.get("change_pct"))
    )
    recent = numeric_list(row.get("recent_closes", []))
    recent_dates = list(row.get("recent_dates", []))
    if not recent_dates or reference_date not in recent_dates:
        recent = recent + [reference_close]
        recent_dates = recent_dates + [format_compact_date(reference_date)]

    merged = dict(row)
    merged.update({
        "source": reference.get("source") or row.get("source"),
        "as_of_date": format_compact_date(reference_date),
        "close": reference_close,
        "previous_close": previous,
        "change": clean_number(change),
        "change_pct": clean_number(change_pct),
        "recent_closes": recent[-7:],
        "recent_dates": recent_dates[-7:],
        "volume": clean_number(reference.get("volume")) or row.get("volume"),
        "trading_value": clean_number(reference.get("trading_value")),
    })
    return merged


def market_status_model(market_data: dict[str, Any]) -> dict[str, Any]:
    indicators = market_data.get("market_indicators", [])
    kospi = find_by_name(indicators, "KOSPI")
    kosdaq = find_by_name(indicators, "KOSDAQ")
    nasdaq = find_by_name(indicators, "Nasdaq")
    sp500 = find_by_name(indicators, "S&P 500")
    usdkrw = find_by_name(indicators, "USD/KRW")
    vix = find_by_name(indicators, "VIX")
    
    # VIX 특수 계산
    vix_score = 0
    if vix:
        vix_close = clean_number(vix.get("close"))
        vix_pct = clean_number(vix.get("change_pct"))
        if (vix_close is not None and vix_close > 20) or (vix_pct is not None and vix_pct >= 10):
            vix_score = 1
            
    score = (
        risk_score(nasdaq, negative_threshold=-2.0, weight=2)
        + risk_score(sp500, negative_threshold=-1.5, weight=2)
        + risk_score(kospi, negative_threshold=-2.0, weight=1)
        + risk_score(kosdaq, negative_threshold=-2.5, weight=1)
        + risk_score(usdkrw, positive_threshold=0.7, weight=1)
        + vix_score
    )
    
    if score >= 4:
        label = "위험"
    elif score >= 2:
        label = "주의"
    else:
        label = "중립"
        
    reasons = market_status_reasons(kospi, kosdaq, nasdaq, sp500, usdkrw, vix)
    return {
        "label": label,
        "score": score,
        "reasons": reasons,
        "reason": " · ".join(reasons[:2]) if reasons else "",
    }


def risk_score(
    row: dict[str, Any] | None,
    *,
    negative_threshold: float | None = None,
    positive_threshold: float | None = None,
    weight: int = 1,
) -> int:
    if not row:
        return 0
    pct = clean_number(row.get("change_pct"))
    if pct is None:
        return 0
    if negative_threshold is not None and pct <= negative_threshold:
        return weight
    if positive_threshold is not None and pct >= positive_threshold:
        return weight
    return 0


def market_status_reasons(
    kospi: dict[str, Any] | None,
    kosdaq: dict[str, Any] | None,
    nasdaq: dict[str, Any] | None,
    sp500: dict[str, Any] | None,
    usdkrw: dict[str, Any] | None,
    vix: dict[str, Any] | None,
) -> list[str]:
    reasons = []
    
    if nasdaq:
        pct = clean_number(nasdaq.get("change_pct"))
        if pct is not None and pct <= -2.0:
            reasons.append("나스닥 급락")
            
    if sp500:
        pct = clean_number(sp500.get("change_pct"))
        if pct is not None and pct <= -1.5:
            reasons.append("S&P 500 급락")
            
    if kospi:
        pct = clean_number(kospi.get("change_pct"))
        if pct is not None and pct <= -2.0:
            reasons.append("KOSPI 급락")
            
    if kosdaq:
        pct = clean_number(kosdaq.get("change_pct"))
        if pct is not None and pct <= -2.5:
            reasons.append("KOSDAQ 급락")
            
    if usdkrw:
        pct = clean_number(usdkrw.get("change_pct"))
        if pct is not None and pct >= 0.7:
            reasons.append("환율 급등")
            
    if vix:
        vix_close = clean_number(vix.get("close"))
        vix_pct = clean_number(vix.get("change_pct"))
        if (vix_close is not None and vix_close > 20) or (vix_pct is not None and vix_pct >= 10):
            reasons.append("VIX 급등")
            
    return reasons


def market_indicator_model(row: dict[str, Any], index: int = 0) -> dict[str, Any]:
    recent = numeric_list(row.get("recent_closes", []))
    latest = clean_number(row.get("close"))
    previous = clean_number(row.get("previous_close"))
    change = clean_number(row.get("change"))
    change_pct = clean_number(row.get("change_pct"))
    name = row.get("name") or row.get("symbol")
    return {
        "name": name,
        "symbol": row.get("symbol"),
        "source": row.get("source"),
        "as_of_date": row.get("as_of_date"),
        "display_order": index,
        "unit": indicator_unit(str(name or row.get("symbol") or "")),
        "risk_tags": indicator_risk_tags(str(name or ""), change_pct),
        "short_comment": indicator_short_comment(str(name or ""), change_pct),
        "price": {
            "latest_close": latest,
            "previous_close": previous,
            "close_7d_ago": first_number(recent),
            "recent_closes": recent,
            "recent_dates": row.get("recent_dates", []),
            "change": change,
            "change_pct": change_pct,
            "trend": trend_from_change(change_pct, recent),
        },
        "volume": clean_number(row.get("volume")),
    }


def holding_model(
    holding: dict[str, Any],
    source: dict[str, Any],
    news: list[dict[str, Any]],
    disclosures: list[dict[str, Any]],
) -> dict[str, Any]:
    market_data = source.get("market_data", {})
    symbol = str(holding.get("symbol", ""))
    name = str(holding.get("name", ""))
    quote = holding_quote(holding, market_data)
    flow = holding_flow(holding, market_data.get("investor_flows", {}))
    holding_news = [
        row for row in news
        if row.get("symbol") == symbol or row.get("name") == name
    ]
    holding_disclosures = [
        row for row in disclosures
        if row.get("symbol") == symbol or row.get("name") == name
    ]

    return {
        "name": name,
        "symbol": symbol,
        "market": holding.get("market"),
        "tier": holding.get("tier"),
        "sector": holding_sector(holding),
        "priority": holding_priority(holding, quote, flow, holding_news, holding_disclosures),
        "factors": holding.get("factors", []),
        "price": quote,
        "flow": {
            "latest": flow,
            "seven_day_total": seven_day_flow_model(flow.get("seven_day_total")),
        },
        "news": holding_news,
        "disclosures": holding_disclosures,
        "impact": impact_model(quote, flow, holding_news, holding_disclosures),
        "primary_issue": primary_issue(quote, flow, holding_news, holding_disclosures),
        "data_status": data_status_model(holding, quote, flow, holding_news, holding_disclosures),
        "analysis_inputs": {
            "price_trend": quote.get("trend"),
            "flow_bias": flow_bias(flow),
            "news_count": len(holding_news),
            "disclosure_count": len(holding_disclosures),
            "tags": sorted(set(holding.get("factors", []))),
        },
    }


def indicator_unit(name: str) -> str:
    if name in {"USD/KRW"}:
        return "KRW"
    if name in {"Gold"}:
        return "USD"
    if name in {"VIX"}:
        return "pct"
    return "index"


def indicator_risk_tags(name: str, change_pct: Any) -> list[str]:
    pct = clean_number(change_pct)
    if pct is None:
        return ["확인 필요"]
    tags = []
    if name in {"KOSPI", "KOSDAQ", "Nasdaq", "S&P 500", "필라델피아반도체지수"}:
        if pct <= -2:
            tags.append("시장 약세")
        elif pct >= 2:
            tags.append("시장 강세")
    if name == "USD/KRW" and pct >= 0.7:
        tags.append("환율 상승")
    if name == "VIX" and pct >= 2:
        tags.append("변동성 상승")
    if name == "Gold" and pct >= 1:
        tags.append("안전자산 강세")
    return tags


def indicator_short_comment(name: str, change_pct: Any) -> str:
    pct = clean_number(change_pct)
    if pct is None:
        return "최신값 확인 필요"
    if pct <= -2:
        return "급락"
    if pct <= -1:
        return "약세"
    if pct >= 2:
        return "강세"
    if pct >= 1:
        return "상승"
    return "보합권"


def holding_sector(holding: dict[str, Any]) -> str:
    factors = set(holding.get("factors", []))
    name = str(holding.get("name", ""))
    if "financial" in factors or "bank" in factors or "insurance" in factors:
        return "financial"
    if "semiconductor" in factors or name in {"삼성전자", "이수페타시스", "Nvidia"}:
        return "semiconductor"
    if "auto" in factors or "currency" in factors or "현대차" in name:
        return "auto_fx"
    if holding.get("market") == "US":
        return "us_portfolio"
    if "bio" in factors or "바이오" in name:
        return "bio"
    return "portfolio"


def holding_priority(
    holding: dict[str, Any],
    quote: dict[str, Any],
    flow: dict[str, Any],
    news: list[dict[str, Any]],
    disclosures: list[dict[str, Any]],
) -> int:
    priority = 0
    pct = clean_number(quote.get("change_pct"))
    if pct is None:
        priority += 1
    else:
        priority += min(int(abs(pct)), 10)
    if holding.get("market") == "KR" and flow_bias(flow) not in {"unknown", "neutral"}:
        priority += 2
    priority += min(len(news), 3)
    priority += min(len(disclosures), 3)
    return priority


def impact_model(
    quote: dict[str, Any],
    flow: dict[str, Any],
    news: list[dict[str, Any]],
    disclosures: list[dict[str, Any]],
) -> dict[str, Any]:
    score = 0
    reasons = []
    pct = clean_number(quote.get("change_pct"))
    if pct is None:
        reasons.append("최근 종가 확인 필요")
    elif pct >= 1:
        score += 1
        reasons.append("가격 상승")
    elif pct <= -1:
        score -= 1
        reasons.append("가격 약세")
    bias = flow_bias(flow)
    if bias in {"institution_foreign_buy", "foreign_buy"}:
        score += 1
        reasons.append("외인 수급 우호")
    elif bias in {"institution_foreign_sell", "foreign_sell"}:
        score -= 1
        reasons.append("외인 수급 부담")
    if disclosures:
        reasons.append(f"공시 {len(disclosures)}건")
    if news:
        reasons.append(f"뉴스 {len(news)}건")
    return {
        "label": impact_label(score),
        "score": score,
        "reasons": reasons[:4],
    }


def impact_label(score: int) -> str:
    if score >= 2:
        return "긍정"
    if score == 1:
        return "중립~긍정"
    if score <= -2:
        return "부정"
    if score == -1:
        return "중립~부정"
    return "중립"


def primary_issue(
    quote: dict[str, Any],
    flow: dict[str, Any],
    news: list[dict[str, Any]],
    disclosures: list[dict[str, Any]],
) -> str:
    pct = clean_number(quote.get("change_pct"))
    if pct is None:
        return "최근 종가 확인 필요"
    bias = flow_bias(flow)
    if pct <= -3 and bias in {"institution_foreign_sell", "foreign_sell"}:
        return "가격 약세와 외인 매도"
    if pct >= 2 and bias in {"institution_foreign_buy", "foreign_buy"}:
        return "가격 상승과 외인 매수"
    if disclosures:
        return "공시 확인"
    if news:
        return "뉴스 확인"
    if pct <= -1:
        return "가격 약세"
    if pct >= 1:
        return "가격 상승"
    return "특이 신호 제한"


def data_status_model(
    holding: dict[str, Any],
    quote: dict[str, Any],
    flow: dict[str, Any],
    news: list[dict[str, Any]],
    disclosures: list[dict[str, Any]],
) -> dict[str, str]:
    market = holding.get("market")
    return {
        "price": "ok" if quote.get("latest_close") is not None else "missing",
        "flow": "ok" if market == "KR" and flow.get("source") else ("not_applicable" if market != "KR" else "missing"),
        "news": "ok" if news else "empty",
        "disclosures": "ok" if disclosures else "empty",
    }


def holding_quote(holding: dict[str, Any], market_data: dict[str, Any]) -> dict[str, Any]:
    symbol = str(holding.get("symbol", ""))
    market = holding.get("market")
    if market == "KR":
        primary = find_by_symbol(market_data.get("kr_quotes", []), symbol)
        reference = find_by_symbol(market_data.get("krx_quotes", []), symbol)
        return domestic_quote_model(primary, reference)
    row = find_by_symbol(market_data.get("us_quotes", []), symbol)
    return quote_model(row or {})


def domestic_quote_model(primary: dict[str, Any] | None, reference: dict[str, Any] | None) -> dict[str, Any]:
    row = primary or reference or {}
    recent = numeric_list(row.get("recent_closes", []))
    latest = clean_number(row.get("price", row.get("close")))
    previous = recent[-2] if len(recent) >= 2 and latest is not None else clean_number(row.get("previous_close"))
    reference_pct = clean_number((reference or {}).get("change_pct"))
    if latest is not None and previous not in (None, 0):
        change = latest - previous
        change_pct = (change / previous) * 100
    else:
        change = clean_number(row.get("change"))
        change_pct = clean_number(row.get("change_pct"))
    if reference_pct is not None and abs(reference_pct) == abs(round(change_pct or reference_pct, 2)):
        change_pct = reference_pct
        if latest is not None and previous not in (None, 0):
            change = latest - previous
    return {
        "source": row.get("source"),
        "reference_source": (reference or {}).get("source"),
        "as_of_date": row.get("as_of_date") or (reference or {}).get("as_of_date"),
        "latest_close": latest,
        "previous_close": previous,
        "close_7d_ago": first_number(recent),
        "recent_closes": recent,
        "recent_dates": row.get("recent_dates", []),
        "change": clean_number(change),
        "change_pct": clean_number(change_pct),
        "trend": trend_from_change(change_pct, recent),
        "volume": clean_number((reference or row).get("volume")),
        "trading_value": clean_number((reference or row).get("trading_value")),
    }


def quote_model(row: dict[str, Any]) -> dict[str, Any]:
    recent = numeric_list(row.get("recent_closes", []))
    latest = clean_number(row.get("close", row.get("price")))
    previous = clean_number(row.get("previous_close"))
    change = clean_number(row.get("change"))
    change_pct = clean_number(row.get("change_pct"))
    return {
        "source": row.get("source"),
        "as_of_date": row.get("as_of_date"),
        "latest_close": latest,
        "previous_close": previous,
        "close_7d_ago": first_number(recent),
        "recent_closes": recent,
        "recent_dates": row.get("recent_dates", []),
        "change": change,
        "change_pct": change_pct,
        "trend": trend_from_change(change_pct, recent),
        "volume": clean_number(row.get("volume")),
        "trading_value": clean_number(row.get("trading_value")),
    }


def holding_flow(holding: dict[str, Any], flows: dict[str, Any]) -> dict[str, Any]:
    symbol = str(holding.get("symbol", ""))
    name = str(holding.get("name", ""))
    row = next(
        (
            flow for flow in flows.get("holdings", [])
            if flow.get("symbol") == symbol or flow.get("name") == name
        ),
        {},
    )
    return flow_model(row)


def flow_model(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": row.get("source"),
        "as_of_date": row.get("as_of_date"),
        "scope": row.get("scope"),
        "market": row.get("market"),
        "symbol": row.get("symbol"),
        "name": row.get("name"),
        "unit": row.get("unit"),
        "individual": clean_number(row.get("individual")),
        "institution": clean_number(row.get("institution")),
        "foreign": clean_number(row.get("foreign")),
        "buy_leader": row.get("buy_leader") or "",
        "sell_leader": row.get("sell_leader") or "",
        "seven_day_total": seven_day_flow_model(row.get("seven_day_total")),
    }


def seven_day_flow_model(row: dict[str, Any] | None) -> dict[str, Any]:
    row = row or {}
    return {
        "available": bool(row.get("available")),
        "trading_days": clean_number(row.get("trading_days")),
        "individual": clean_number(row.get("individual")),
        "institution": clean_number(row.get("institution")),
        "foreign": clean_number(row.get("foreign")),
    }


def flow_bias(flow: dict[str, Any]) -> str:
    institution = flow.get("institution")
    foreign = flow.get("foreign")
    if institution is None and foreign is None:
        return "unknown"
    if (institution or 0) > 0 and (foreign or 0) > 0:
        return "institution_foreign_buy"
    if (institution or 0) < 0 and (foreign or 0) < 0:
        return "institution_foreign_sell"
    if (foreign or 0) > 0:
        return "foreign_buy"
    if (foreign or 0) < 0:
        return "foreign_sell"
    if (institution or 0) > 0:
        return "institution_buy"
    if (institution or 0) < 0:
        return "institution_sell"
    return "neutral"


def find_by_symbol(rows: list[dict[str, Any]], symbol: str) -> dict[str, Any] | None:
    return next((row for row in rows if row.get("symbol") == symbol), None)


def find_by_name(rows: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    return next((row for row in rows if row.get("name") == name), None)


def numeric_list(values: list[Any]) -> list[float | None]:
    return [clean_number(value) for value in values]


def first_number(values: list[float | None]) -> float | None:
    return next((value for value in values if value is not None), None)


def normalize_date_token(value: Any) -> str:
    text = str(value or "").strip()
    digits = "".join(char for char in text if char.isdigit())
    return digits[:8]


def format_compact_date(value: Any) -> str:
    digits = normalize_date_token(value)
    if len(digits) != 8:
        return str(value or "")
    return f"{digits[:4]}-{digits[4:6]}-{digits[6:]}"


def clean_number(value: Any) -> float | int | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    if number.is_integer():
        return int(number)
    return round(number, 4)


def trend_from_change(change_pct: Any, recent: list[float | None]) -> str:
    pct = clean_number(change_pct)
    if pct is not None:
        if pct >= 1:
            return "up"
        if pct <= -1:
            return "down"
    clean_recent = [value for value in recent if value is not None]
    if len(clean_recent) >= 2:
        if clean_recent[-1] > clean_recent[0]:
            return "up_7d"
        if clean_recent[-1] < clean_recent[0]:
            return "down_7d"
    return "flat"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument(
        "--source",
        default=None,
        help="Path to source.json. Defaults to data/incoming/DATE/source.json.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Path to write view_model.json. Defaults to data/reports/DATE/view_model.json.",
    )
    args = parser.parse_args(argv)

    source_path = Path(args.source) if args.source else INCOMING_DIR / args.date / "source.json"
    output_path = Path(args.output) if args.output else REPORTS_DIR / args.date / "view_model.json"
    if not source_path.exists():
        print(f"source not found: {source_path}", file=sys.stderr)
        return 1

    source = json.loads(source_path.read_text(encoding="utf-8"))
    view_model = build_view_model(source)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(view_model, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
