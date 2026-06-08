from __future__ import annotations

import argparse
import datetime as dt
import html
import io
import json
import math
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PORTFOLIO_PATH = ROOT / "config" / "portfolio.yaml"
INCOMING_DIR = ROOT / "data" / "incoming"
CACHE_DIR = ROOT / "data" / "cache"
DART_API_BASE = "https://opendart.fss.or.kr/api"
KRX_OPEN_API_BASE = "https://data-dbg.krx.co.kr/svc/apis"
KRX_STOCK_API_PATHS = {
    "KOSPI": "sto/stk_bydd_trd",
    "KOSDAQ": "sto/ksq_bydd_trd",
}
KRX_INDEX_API_PATHS = {
    "KOSPI": "idx/kospi_dd_trd",
    "KOSDAQ": "idx/kosdaq_dd_trd",
}
MARKET_INDICATORS = {
    "^KS11": "KOSPI",
    "^KQ11": "KOSDAQ",
    "^IXIC": "Nasdaq",
    "^GSPC": "S&P 500",
    "^VIX": "VIX",
    "GC=F": "Gold",
    "KRW=X": "USD/KRW",
    "^SOX": "필라델피아반도체지수",
}

RSS_FEEDS = [
    ("CNBC Markets", "https://www.cnbc.com/id/100003114/device/rss/rss.html"),
]

DART_STOCK_CODE_FALLBACKS = {
    "005387": "005380",  # 현대차2우B -> 현대차
    "011785": "011780",  # 금호석유화학우 -> 금호석유화학
}

KOSDAQ_SYMBOLS = {"048410"}
INVESTOR_NAME_KO = {
    "individual": "개인",
    "institution": "기관",
    "foreign": "외국인",
}


def now_kst() -> dt.datetime:
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=9)))


def load_env() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def read_portfolio() -> list[dict[str, Any]]:
    holdings: list[dict[str, Any]] = []
    section = None
    current: dict[str, Any] | None = None

    for raw_line in PORTFOLIO_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line in {"domestic:", "overseas:"}:
            section = line[:-1]
            continue
        if line.startswith("- "):
            if current:
                holdings.append(current)
            current = {"market": "KR" if section == "domestic" else "US"}
            line = line[2:]
        if current is None or ":" not in line:
            continue
        key, value = line.split(":", 1)
        current[key.strip()] = parse_yaml_value(value.strip())

    if current:
        holdings.append(current)
    return holdings


def parse_yaml_value(value: str) -> Any:
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value.startswith("[") and value.endswith("]"):
        items = [item.strip().strip('"') for item in value[1:-1].split(",")]
        return [item for item in items if item]
    if value.isdigit():
        return int(value)
    return value


def fetch_url(url: str, timeout: int = 12) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 morning-investment-briefing/0.1",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read()
        charset = response.headers.get_content_charset()
        if charset:
            return raw.decode(charset, errors="replace")
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return raw.decode("euc-kr", errors="replace")


def fetch_bytes(url: str, timeout: int = 20) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 morning-investment-briefing/0.1",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def fetch_json(url: str, headers: dict[str, str], timeout: int = 12) -> dict[str, Any]:
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def collect_yfinance(
    holdings: list[dict[str, Any]],
    offline: bool,
    run_date: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    quality: list[dict[str, Any]] = []
    symbols = [h["symbol"] for h in holdings if h.get("market") == "US" and h.get("symbol") != "UNCONFIRMED"]

    if offline:
        return rows, [{"source": "yfinance", "status": "skipped", "reason": "offline mode"}]

    try:
        import yfinance as yf  # type: ignore
    except ImportError:
        return rows, [{"source": "yfinance", "status": "failed", "reason": "package not installed"}]

    for symbol in symbols:
        row, error = fetch_yfinance_quote(yf, symbol, run_date)
        if row:
            rows.append(row)
        if error:
            quality.append(error)
    return rows, quality


def collect_yfinance_news(
    holdings: list[dict[str, Any]],
    offline: bool,
    per_symbol: int = 3,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    quality: list[dict[str, Any]] = []
    symbols = [h["symbol"] for h in holdings if h.get("market") == "US" and h.get("symbol") != "UNCONFIRMED"]

    if offline:
        return rows, [{"source": "yfinance_news", "status": "skipped", "reason": "offline mode"}]

    try:
        import yfinance as yf  # type: ignore
    except ImportError:
        return rows, [{"source": "yfinance_news", "status": "failed", "reason": "package not installed"}]

    for symbol in symbols:
        try:
            ticker = yf.Ticker(symbol)
            count = 0
            for item in getattr(ticker, "news", []) or []:
                row = normalize_yfinance_news(symbol, item)
                if row is None:
                    continue
                rows.append(row)
                count += 1
                if count >= per_symbol:
                    break
        except Exception as exc:  # noqa: BLE001
            quality.append({"source": "yfinance_news", "symbol": symbol, "status": "failed", "reason": str(exc)})
    return rows, quality


def normalize_yfinance_news(symbol: str, item: dict[str, Any]) -> dict[str, Any] | None:
    content = item.get("content") if isinstance(item.get("content"), dict) else {}
    title = item.get("title") or content.get("title")
    if not title:
        return None

    link = item.get("link")
    canonical_url = content.get("canonicalUrl") if isinstance(content.get("canonicalUrl"), dict) else {}
    click_url = content.get("clickThroughUrl") if isinstance(content.get("clickThroughUrl"), dict) else {}
    url = link or canonical_url.get("url") or click_url.get("url") or ""

    publisher = item.get("publisher") or content.get("provider", {}).get("displayName")
    publish_time = item.get("providerPublishTime") or content.get("pubDate")
    if isinstance(publish_time, int):
        published_at = dt.datetime.fromtimestamp(publish_time, dt.timezone.utc).isoformat()
    else:
        published_at = publish_time or ""

    return {
        "source": "yfinance_news",
        "symbol": symbol,
        "publisher": publisher or "Yahoo Finance",
        "title": str(title).strip(),
        "url": str(url).strip(),
        "published_at": str(published_at).strip(),
    }


def collect_market_indicators(
    offline: bool,
    run_date: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    quality: list[dict[str, Any]] = []

    if offline:
        return rows, [{"source": "yfinance_indicators", "status": "skipped", "reason": "offline mode"}]

    try:
        import yfinance as yf  # type: ignore
    except ImportError:
        return rows, [{"source": "yfinance_indicators", "status": "failed", "reason": "package not installed"}]

    for symbol, name in MARKET_INDICATORS.items():
        row, error = fetch_yfinance_quote(yf, symbol, run_date)
        if row:
            row["name"] = name
            rows.append(row)
        if error:
            error["source"] = "yfinance_indicators"
            quality.append(error)
    return rows, quality


def fetch_yfinance_quote(
    yf: Any,
    symbol: str,
    max_date: str | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    try:
        ticker = yf.Ticker(symbol)
        history = ticker.history(period="10d", interval="1d", auto_adjust=False)
        if history.empty:
            return None, {"source": "yfinance", "symbol": symbol, "status": "missing", "reason": "empty history"}
        history = filter_history_by_max_date(history, max_date)
        valid_history = history[
            history["Close"].apply(is_valid_close)
        ]
        if valid_history.empty:
            return None, {
                "source": "yfinance",
                "symbol": symbol,
                "status": "missing",
                "reason": "history has no valid close",
            }
        last = valid_history.iloc[-1]
        previous = valid_history.iloc[-2] if len(valid_history) > 1 else None
        close = float(last["Close"])
        previous_close = float(previous["Close"]) if previous is not None else None
        change = None if previous_close is None else close - previous_close
        change_pct = None if previous_close in (None, 0) else ((close - previous_close) / previous_close) * 100
        recent_history = valid_history.tail(7)
        recent_closes = [round(float(value), 4) for value in recent_history["Close"]]
        recent_dates = [format_yfinance_date(index) for index in recent_history.index]
        row = {
            "symbol": symbol,
            "source": "yfinance",
            "as_of_date": format_yfinance_date(valid_history.index[-1]),
            "close": round(close, 4),
            "previous_close": round(previous_close, 4) if previous_close is not None else None,
            "change": round(change, 4) if change is not None else None,
            "change_pct": round(change_pct, 2) if change_pct is not None else None,
            "recent_closes": recent_closes,
            "recent_dates": recent_dates,
            "volume": int(last["Volume"]) if "Volume" in last and is_finite_number(last["Volume"]) else None,
        }
        warning = None
        if len(valid_history) != len(history):
            warning = {
                "source": "yfinance",
                "symbol": symbol,
                "status": "partial",
                "reason": "ignored history rows with invalid close",
            }
        return row, warning
    except Exception as exc:  # noqa: BLE001
        return None, {"source": "yfinance", "symbol": symbol, "status": "failed", "reason": str(exc)}


def format_yfinance_date(value: Any) -> str:
    date_value = value.date() if hasattr(value, "date") else value
    return str(date_value)


def filter_history_by_max_date(history: Any, max_date: str | None) -> Any:
    if not max_date or getattr(history, "empty", True):
        return history
    max_date_value = dt.date.fromisoformat(max_date)
    return history[
        [dt.date.fromisoformat(format_yfinance_date(index)) <= max_date_value for index in history.index]
    ]


def is_finite_number(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def is_valid_close(value: Any) -> bool:
    try:
        close = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(close) and close > 0


def collect_naver(
    holdings: list[dict[str, Any]],
    offline: bool,
    run_date: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    quality: list[dict[str, Any]] = []

    if offline:
        return rows, [{"source": "naver_finance", "status": "skipped", "reason": "offline mode"}]

    try:
        import yfinance as yf  # type: ignore
    except ImportError:
        yf = None

    for holding in [h for h in holdings if h.get("market") == "KR"]:
        symbol = holding["symbol"]
        url = f"https://finance.naver.com/item/main.naver?code={symbol}"
        try:
            page = fetch_url(url)
            price = extract_first(page, r'<p class="no_today">.*?<span class="blind">([\d,]+)</span>')
            rate = extract_first(page, r'<p class="no_exday">.*?<span class="blind">([+-]?\d+\.\d+)</span>')
            current_price = int(price.replace(",", "")) if price else None
            change_pct = float(rate) if rate else None
            previous_close = None
            change = None
            if current_price is not None and change_pct not in (None, -100):
                previous_close = current_price / (1 + (change_pct / 100))
                change = current_price - previous_close
            row = {
                "symbol": symbol,
                "name": holding["name"],
                "source": "naver_finance",
                "url": url,
                "price": current_price,
                "previous_close": round(previous_close, 4) if previous_close is not None else None,
                "change": round(change, 4) if change is not None else None,
                "change_pct": change_pct,
            }
            if yf is not None:
                history, history_error = fetch_yfinance_quote(yf, kr_yfinance_symbol(symbol), run_date)
                if history and history.get("recent_closes"):
                    use_history_close = current_price is None or is_backfill_run(run_date)
                    row["recent_closes"] = history["recent_closes"][:-1] + (
                        [history["recent_closes"][-1]] if use_history_close else [current_price]
                    )
                    row["recent_dates"] = history.get("recent_dates", [])
                    row["as_of_date"] = history.get("as_of_date")
                    if use_history_close:
                        row.update({
                            "source": "naver_finance_yfinance_fallback" if current_price is None else "yfinance_backfill",
                            "price": history.get("close"),
                            "previous_close": history.get("previous_close"),
                            "change": history.get("change"),
                            "change_pct": history.get("change_pct"),
                        })
                        quality.append({
                            "source": "naver_finance",
                            "symbol": symbol,
                            "status": "partial",
                            "reason": (
                                "Naver Finance price missing; used latest valid yfinance close"
                                if current_price is None
                                else "backfill run; used yfinance close at or before report date"
                            ),
                        })
                if history_error:
                    quality.append({
                        "source": "naver_finance_history",
                        "symbol": symbol,
                        "status": history_error.get("status", "failed"),
                        "reason": history_error.get("reason", "history unavailable"),
                    })
            rows.append(row)
        except Exception as exc:  # noqa: BLE001
            quality.append({"source": "naver_finance", "symbol": symbol, "status": "failed", "reason": str(exc)})
    return rows, quality


def kr_yfinance_symbol(symbol: str) -> str:
    suffix = "KQ" if symbol in KOSDAQ_SYMBOLS else "KS"
    return f"{symbol}.{suffix}"


def is_backfill_run(run_date: str | None) -> bool:
    return bool(run_date and dt.date.fromisoformat(run_date) < now_kst().date())


def collect_naver_news(
    holdings: list[dict[str, Any]],
    offline: bool,
    per_symbol: int = 3,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    quality: list[dict[str, Any]] = []

    if offline:
        return rows, [{"source": "naver_search_news", "status": "skipped", "reason": "offline mode"}]

    client_id = os.getenv("NAVER_CLIENT_ID")
    client_secret = os.getenv("NAVER_CLIENT_SECRET")
    if not client_id or not client_secret:
        return rows, [{
            "source": "naver_search_news",
            "status": "skipped",
            "reason": "NAVER_CLIENT_ID or NAVER_CLIENT_SECRET not set",
        }]

    for holding in [h for h in holdings if h.get("market") == "KR"]:
        query = naver_news_query(holding)
        params = {
            "query": query,
            "display": str(per_symbol),
            "start": "1",
            "sort": "date",
        }
        url = f"https://openapi.naver.com/v1/search/news.json?{urlencode(params)}"
        try:
            payload = fetch_json(url, {
                "X-Naver-Client-Id": client_id,
                "X-Naver-Client-Secret": client_secret,
            })
            for item in payload.get("items", []):
                rows.append({
                    "source": "naver_search_news",
                    "symbol": holding["symbol"],
                    "name": holding["name"],
                    "query": query,
                    "title": clean_text(item.get("title", "")),
                    "url": item.get("originallink") or item.get("link") or "",
                    "naver_url": item.get("link") or "",
                    "description": clean_text(item.get("description", "")),
                    "published_at": item.get("pubDate", ""),
                })
        except Exception as exc:  # noqa: BLE001
            quality.append({
                "source": "naver_search_news",
                "symbol": holding["symbol"],
                "status": "failed",
                "reason": str(exc),
            })
    return rows, quality


def naver_news_query(holding: dict[str, Any]) -> str:
    name = str(holding["name"])
    if holding.get("symbol") == "005387":
        return "현대차"
    if name.endswith("우"):
        return name[:-1]
    if name.endswith("우B"):
        return name[:-2]
    return name


def collect_krx_open_api_reference(
    holdings: list[dict[str, Any]],
    run_date: str,
    offline: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    stock_rows: list[dict[str, Any]] = []
    index_rows: list[dict[str, Any]] = []
    quality: list[dict[str, Any]] = []

    if offline:
        return stock_rows, index_rows, [{"source": "krx_open_api", "status": "skipped", "reason": "offline mode"}]
    if not os.getenv("KRX_AUTH_KEY"):
        return stock_rows, index_rows, [{"source": "krx_open_api", "status": "skipped", "reason": "KRX_AUTH_KEY not set"}]

    dates = candidate_market_dates(run_date)
    domestic_names = {
        holding["symbol"]: holding["name"]
        for holding in holdings
        if holding.get("market") == "KR"
    }

    for market, api_path in KRX_STOCK_API_PATHS.items():
        rows, error = first_krx_rows(api_path, dates, ("TDD_CLSPRC",))
        if not rows:
            quality.append({
                "source": "krx_open_api",
                "market": market,
                "status": "missing",
                "reason": error or "empty stock data",
            })
            continue
        for row in rows:
            symbol = str(row.get("ISU_CD") or row.get("ISU_SRT_CD") or "").strip()
            if symbol not in domestic_names:
                continue
            stock_rows.append({
                "symbol": symbol,
                "name": domestic_names[symbol],
                "source": "krx_open_api",
                "as_of_date": str(row.get("BAS_DD") or row.get("TRD_DD") or ""),
                "price": parse_int_value(row.get("TDD_CLSPRC")),
                "change": parse_int_value(row.get("CMPPREVDD_PRC")),
                "change_pct": safe_float(str(row.get("FLUC_RT", "")).replace(",", "")),
                "volume": parse_int_value(row.get("ACC_TRDVOL")),
                "trading_value": parse_int_value(row.get("ACC_TRDVAL")),
            })

    for name, api_path in KRX_INDEX_API_PATHS.items():
        rows, error = first_krx_rows(api_path, dates, ("CLSPRC_IDX", "TDD_CLSPRC"))
        if not rows:
            quality.append({
                "source": "krx_open_api",
                "index": name,
                "status": "missing",
                "reason": error or "empty index data",
            })
            continue
        row = rows[0]
        index_rows.append({
            "name": name,
            "source": "krx_open_api",
            "as_of_date": str(row.get("BAS_DD") or row.get("TRD_DD") or ""),
            "close": safe_float(str(row.get("CLSPRC_IDX") or row.get("TDD_CLSPRC") or "").replace(",", "")),
            "change": safe_float(str(row.get("CMPPREVDD_IDX") or row.get("CMPPREVDD_PRC") or "").replace(",", "")),
            "change_pct": safe_float(str(row.get("FLUC_RT") or "").replace(",", "")),
            "volume": parse_int_value(row.get("ACC_TRDVOL")),
            "trading_value": parse_int_value(row.get("ACC_TRDVAL")),
        })

    return stock_rows, index_rows, quality


def collect_krx_reference(
    holdings: list[dict[str, Any]],
    run_date: str,
    offline: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    stock_rows, index_rows, quality = collect_krx_open_api_reference(holdings, run_date, offline)
    if offline or (stock_rows and index_rows):
        return stock_rows, index_rows, quality

    fallback_rows, fallback_indices, fallback_quality = collect_pykrx_fallback_reference(holdings, run_date)
    existing_symbols = {row.get("symbol") for row in stock_rows}
    existing_indices = {row.get("name") for row in index_rows}
    merged_rows = stock_rows + [row for row in fallback_rows if row.get("symbol") not in existing_symbols]
    merged_indices = index_rows + [row for row in fallback_indices if row.get("name") not in existing_indices]
    return merged_rows, merged_indices, quality + fallback_quality


def collect_pykrx_fallback_reference(
    holdings: list[dict[str, Any]],
    run_date: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    stock_rows: list[dict[str, Any]] = []
    index_rows: list[dict[str, Any]] = []
    quality: list[dict[str, Any]] = []

    if not os.getenv("KRX_ID") or not os.getenv("KRX_PW"):
        return stock_rows, index_rows, [{
            "source": "pykrx_fallback",
            "status": "skipped",
            "reason": "KRX_ID or KRX_PW not set",
        }]

    try:
        from pykrx import stock  # type: ignore
    except ImportError:
        return stock_rows, index_rows, [{
            "source": "pykrx_fallback",
            "status": "failed",
            "reason": "package not installed",
        }]

    dates = candidate_market_dates(run_date)
    domestic_names = {
        holding["symbol"]: holding["name"]
        for holding in holdings
        if holding.get("market") == "KR"
    }

    stock_frames: list[tuple[str, Any, str]] = []
    for market in ("KOSPI", "KOSDAQ"):
        for date in dates:
            try:
                frame = stock.get_market_ohlcv_by_ticker(date, market=market)
            except Exception as exc:  # noqa: BLE001
                quality.append({
                    "source": "pykrx_fallback",
                    "market": market,
                    "status": "failed",
                    "reason": str(exc),
                })
                break
            if pykrx_frame_has_valid_close(frame, "종가"):
                stock_frames.append((market, frame, date))
                break

    seen_symbols: set[str] = set()
    for _market, frame, date in stock_frames:
        for symbol, name in domestic_names.items():
            if symbol in seen_symbols or symbol not in frame.index:
                continue
            row = frame.loc[symbol]
            stock_rows.append({
                "symbol": symbol,
                "name": name,
                "source": "pykrx_fallback",
                "as_of_date": date,
                "price": parse_int_value(row.get("종가")),
                "change": parse_int_value(row.get("대비")),
                "change_pct": safe_float(row.get("등락률")),
                "volume": parse_int_value(row.get("거래량")),
                "trading_value": parse_int_value(row.get("거래대금")),
            })
            seen_symbols.add(symbol)

    for index_code, name in (("1001", "KOSPI"), ("2001", "KOSDAQ")):
        for date in dates:
            try:
                frame = stock.get_index_ohlcv_by_date(date, date, index_code)
            except Exception as exc:  # noqa: BLE001
                quality.append({
                    "source": "pykrx_fallback",
                    "index": name,
                    "status": "failed",
                    "reason": str(exc),
                })
                break
            if not pykrx_frame_has_valid_close(frame, "종가"):
                continue
            row = frame.iloc[-1]
            index_rows.append({
                "name": name,
                "source": "pykrx_fallback",
                "as_of_date": date,
                "close": safe_float(row.get("종가")),
                "change": safe_float(row.get("등락폭")),
                "change_pct": safe_float(row.get("등락률")),
                "volume": parse_int_value(row.get("거래량")),
                "trading_value": parse_int_value(row.get("거래대금")),
            })
            break

    return stock_rows, index_rows, quality


def first_krx_rows(
    api_path: str,
    dates: list[str],
    close_fields: tuple[str, ...],
) -> tuple[list[dict[str, Any]], str | None]:
    last_error = None
    for date in dates:
        payload = request_krx_open_api(api_path, {"basDd": date})
        if payload.get("__error"):
            last_error = str(payload["__error"])
            continue
        rows = krx_result_rows(payload)
        if rows and any(row_has_valid_close(row, close_fields) for row in rows):
            return rows, None
    return [], last_error


def row_has_valid_close(row: dict[str, Any], fields: tuple[str, ...]) -> bool:
    return any(is_valid_close(str(row.get(field, "")).replace(",", "")) for field in fields)


def pykrx_frame_has_valid_close(frame: Any, column: str) -> bool:
    if getattr(frame, "empty", True) or not hasattr(frame, "__contains__") or column not in frame:
        return False
    try:
        return any(is_valid_close(value) for value in frame[column])
    except Exception:  # noqa: BLE001
        return False


def collect_investor_flows(
    holdings: list[dict[str, Any]],
    run_date: str,
    offline: bool,
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    flows = {"markets": [], "holdings": []}
    if offline:
        return flows, [{"source": "krx_investor_flows", "status": "skipped", "reason": "offline mode"}]

    if not os.getenv("KRX_AUTH_KEY"):
        quality = [{"source": "krx_investor_flows", "status": "skipped", "reason": "KRX_AUTH_KEY not set"}]
        fallback_flows, fallback_quality = collect_pykrx_fallback_investor_flows(holdings, run_date)
        return fallback_flows, quality + fallback_quality

    flows, quality = collect_investor_flows_from_krx_open_api(holdings, run_date)
    if flows["markets"] or flows["holdings"]:
        return flows, quality

    fallback_flows, fallback_quality = collect_pykrx_fallback_investor_flows(holdings, run_date)
    return fallback_flows, quality + fallback_quality


def collect_investor_flows_from_krx_open_api(
    holdings: list[dict[str, Any]],
    run_date: str,
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    flows = {"markets": [], "holdings": []}
    quality: list[dict[str, Any]] = []
    market_api_path = os.getenv("KRX_INVESTOR_MARKET_API_PATH")
    holding_api_path = os.getenv("KRX_INVESTOR_HOLDING_API_PATH")

    if not market_api_path and not holding_api_path:
        return flows, [{
            "source": "krx_investor_flows",
            "status": "skipped",
            "reason": "KRX investor flow Open API path not configured",
        }]

    dates = candidate_market_dates(run_date)
    if market_api_path:
        for market in ("KOSPI", "KOSDAQ"):
            row = fetch_krx_market_investor_flow(market_api_path, market, dates)
            if row:
                flows["markets"].append(row)
            else:
                quality.append({
                    "source": "krx_investor_flows",
                    "scope": "market",
                    "market": market,
                    "status": "missing",
                    "reason": "empty investor flow data",
                })

    if holding_api_path:
        for holding in holdings:
            if holding.get("market") != "KR":
                continue
            symbol = str(holding["symbol"])
            row = fetch_krx_holding_investor_flow(holding_api_path, symbol, str(holding["name"]), dates)
            if row:
                flows["holdings"].append(row)
            else:
                quality.append({
                    "source": "krx_investor_flows",
                    "scope": "holding",
                    "symbol": symbol,
                    "name": holding["name"],
                    "status": "missing",
                    "reason": "empty investor flow data",
                })

    return flows, quality


def fetch_krx_market_investor_flow(api_path: str, market: str, dates: list[str]) -> dict[str, Any] | None:
    for date in dates:
        payload = request_krx_open_api(api_path, krx_query_params(date, market=market))
        row = investor_flow_from_krx_rows(krx_result_rows(payload))
        if row:
            row.update({"scope": "market", "market": market, "as_of_date": date})
            return row
    return None


def fetch_krx_holding_investor_flow(api_path: str, symbol: str, name: str, dates: list[str]) -> dict[str, Any] | None:
    for date in dates:
        payload = request_krx_open_api(api_path, krx_query_params(date, symbol=symbol))
        row = investor_flow_from_krx_rows(krx_result_rows(payload))
        if row:
            row.update({"scope": "holding", "symbol": symbol, "name": name, "as_of_date": date})
            return row
    return None


def collect_pykrx_fallback_investor_flows(
    holdings: list[dict[str, Any]],
    run_date: str,
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    flows = {"markets": [], "holdings": []}
    quality: list[dict[str, Any]] = []

    if not os.getenv("KRX_ID") or not os.getenv("KRX_PW"):
        return flows, [{
            "source": "pykrx_fallback",
            "status": "skipped",
            "reason": "KRX_ID or KRX_PW not set",
        }]

    try:
        from pykrx import stock  # type: ignore
    except ImportError:
        return flows, [{
            "source": "pykrx_fallback",
            "status": "failed",
            "reason": "package not installed",
        }]

    dates = candidate_market_dates(run_date)
    for market in ("KOSPI", "KOSDAQ"):
        row = fetch_pykrx_market_investor_flow(stock, market, dates)
        if row:
            flows["markets"].append(row)
        else:
            quality.append({
                "source": "pykrx_fallback",
                "scope": "market",
                "market": market,
                "status": "missing",
                "reason": "empty investor flow data",
            })

    for holding in holdings:
        if holding.get("market") != "KR":
            continue
        symbol = str(holding["symbol"])
        row = fetch_pykrx_holding_investor_flow(stock, symbol, str(holding["name"]), dates)
        if row:
            flows["holdings"].append(row)
        else:
            quality.append({
                "source": "pykrx_fallback",
                "scope": "holding",
                "symbol": symbol,
                "name": holding["name"],
                "status": "missing",
                "reason": "empty investor flow data",
            })

    return flows, quality


def fetch_pykrx_market_investor_flow(stock: Any, market: str, dates: list[str]) -> dict[str, Any] | None:
    for date in dates:
        try:
            frame = stock.get_market_trading_value_by_investor(date, date, market)
        except Exception:
            continue
        row = investor_flow_from_pykrx_frame(frame)
        if row:
            row.update({"scope": "market", "market": market, "as_of_date": date})
            seven_day_total = pykrx_seven_day_flow_total(stock, market, date)
            if seven_day_total:
                row["seven_day_total"] = seven_day_total
            return row
    return None


def fetch_pykrx_holding_investor_flow(stock: Any, symbol: str, name: str, dates: list[str]) -> dict[str, Any] | None:
    for date in dates:
        try:
            frame = stock.get_market_trading_value_by_date(date, date, symbol)
        except Exception:
            continue
        row = investor_flow_from_pykrx_frame(frame)
        if row:
            row.update({"scope": "holding", "symbol": symbol, "name": name, "as_of_date": date})
            seven_day_total = pykrx_seven_day_flow_total(stock, symbol, date)
            if seven_day_total:
                row["seven_day_total"] = seven_day_total
            return row
    return None


def pykrx_seven_day_flow_total(stock: Any, ticker: str, end_date: str) -> dict[str, Any] | None:
    start_date = (
        dt.datetime.strptime(end_date, "%Y%m%d").date() - dt.timedelta(days=14)
    ).strftime("%Y%m%d")
    try:
        frame = stock.get_market_trading_value_by_date(start_date, end_date, ticker)
    except Exception:
        return None
    return investor_flow_sum_from_pykrx_frame(frame)


def investor_flow_sum_from_pykrx_frame(frame: Any, limit: int = 7) -> dict[str, Any] | None:
    if getattr(frame, "empty", True):
        return None
    recent = frame.tail(limit)
    totals = {
        "individual": pykrx_column_sum(recent, ("개인",)),
        "institution": pykrx_column_sum(recent, ("기관합계", "기관")),
        "foreign": pykrx_column_sum(recent, ("외국인합계", "외국인")),
    }
    if all(value is None for value in totals.values()):
        return None
    return {
        "available": True,
        "trading_days": len(recent),
        "individual": totals["individual"] or 0,
        "institution": totals["institution"] or 0,
        "foreign": totals["foreign"] or 0,
    }


def pykrx_column_sum(frame: Any, labels: tuple[str, ...]) -> int | None:
    for label in labels:
        if label in frame.columns:
            total = 0
            found = False
            for value in frame[label]:
                parsed = parse_int_value(value)
                if parsed is not None:
                    total += parsed
                    found = True
            return total if found else None
    return None


def investor_flow_from_pykrx_frame(frame: Any) -> dict[str, Any] | None:
    if getattr(frame, "empty", True):
        return None

    totals = {
        "individual": pykrx_value(frame, ("개인",)),
        "institution": pykrx_value(frame, ("기관합계", "기관")),
        "foreign": pykrx_value(frame, ("외국인합계", "외국인")),
    }
    if totals["institution"] is None:
        totals["institution"] = pykrx_institution_sum(frame)
    if all(value is None for value in totals.values()):
        return None

    numeric_totals = {key: value or 0 for key, value in totals.items()}
    row = {
        "source": "pykrx_fallback",
        "unit": "KRW",
        "individual": numeric_totals["individual"],
        "institution": numeric_totals["institution"],
        "foreign": numeric_totals["foreign"],
    }
    buy_key = max(numeric_totals, key=lambda key: numeric_totals[key])
    sell_key = min(numeric_totals, key=lambda key: numeric_totals[key])
    row["buy_leader"] = INVESTOR_NAME_KO[buy_key] if numeric_totals[buy_key] > 0 else ""
    row["sell_leader"] = INVESTOR_NAME_KO[sell_key] if numeric_totals[sell_key] < 0 else ""
    return row


def pykrx_value(frame: Any, labels: tuple[str, ...]) -> int | None:
    for label in labels:
        if label in frame.index and "순매수" in frame.columns:
            return parse_int_value(frame.loc[label, "순매수"])
        if label in frame.columns:
            values = frame[label]
            if len(values) > 0:
                return parse_int_value(values.iloc[-1])
    return None


def pykrx_institution_sum(frame: Any) -> int | None:
    if "순매수" not in frame.columns:
        return None
    excluded = {"개인", "외국인", "외국인합계", "기타법인", "전체"}
    total = 0
    found = False
    for label in frame.index:
        if str(label) in excluded:
            continue
        value = parse_int_value(frame.loc[label, "순매수"])
        if value is not None:
            total += value
            found = True
    return total if found else None


def request_krx_open_api(api_path: str, params: dict[str, str], timeout: int = 20) -> dict[str, Any]:
    auth_key = os.getenv("KRX_AUTH_KEY")
    if not auth_key:
        return {}
    base_url = os.getenv("KRX_OPEN_API_BASE", KRX_OPEN_API_BASE).rstrip("/")
    normalized_path = api_path.strip().strip("/")
    if normalized_path.startswith("apis/"):
        normalized_path = normalized_path[5:]
    last_error = None
    for url in krx_open_api_urls(base_url, normalized_path, params):
        try:
            return fetch_json(url, headers={"AUTH_KEY": auth_key, "User-Agent": "Mozilla/5.0 KSS/0.1"}, timeout=timeout)
        except urllib.error.HTTPError as exc:
            last_error = f"HTTP {exc.code}: {exc.reason}"
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
    return {"__error": last_error or "request failed"}


def krx_open_api_urls(base_url: str, api_path: str, params: dict[str, str]) -> list[str]:
    query = urlencode(params)
    path_url = f"{base_url}/{api_path}"
    if api_path.endswith(".json"):
        return [f"{path_url}?{query}"]
    return [
        f"{path_url}?{query}",
        f"{path_url}.json?{query}",
    ]


def krx_query_params(date: str, market: str | None = None, symbol: str | None = None) -> dict[str, str]:
    params = {"basDd": date}
    if market:
        params.update({
            "mktId": {"KOSPI": "STK", "KOSDAQ": "KSQ"}.get(market, market),
            "mktNm": market,
        })
    if symbol:
        params.update({"isuCd": symbol, "isuSrtCd": symbol})
    return params


def krx_result_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    output = payload.get("output")
    if isinstance(output, dict):
        for key in ("result", "OutBlock_1"):
            rows = output.get(key)
            if isinstance(rows, list):
                return [row for row in rows if isinstance(row, dict)]
    for key in ("result", "OutBlock_1"):
        rows = payload.get(key)
        if isinstance(rows, list):
            return [row for row in rows if isinstance(row, dict)]
    return []


def investor_flow_from_krx_rows(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    totals = {"individual": 0, "institution": 0, "foreign": 0}
    found = False
    for row in rows:
        values = {
            "individual": investor_value_from_krx_row(row, ("개인", "IND", "INDI", "INVST_TP_CD_1000")),
            "institution": investor_value_from_krx_row(row, ("기관", "기관합계", "INS", "INST", "INVST_TP_CD_3000")),
            "foreign": investor_value_from_krx_row(row, ("외국인", "외국인합계", "FRG", "FOR", "INVST_TP_CD_9000")),
        }
        for key, value in values.items():
            if value is not None:
                totals[key] += value
                found = True
    if not found:
        return None
    row = {
        "source": "krx_open_api",
        "unit": "KRW",
        "individual": totals["individual"],
        "institution": totals["institution"],
        "foreign": totals["foreign"],
    }
    numeric_values = {key: value for key, value in totals.items()}
    buy_key = max(numeric_values, key=lambda key: numeric_values[key])
    sell_key = min(numeric_values, key=lambda key: numeric_values[key])
    row["buy_leader"] = INVESTOR_NAME_KO[buy_key] if numeric_values[buy_key] > 0 else ""
    row["sell_leader"] = INVESTOR_NAME_KO[sell_key] if numeric_values[sell_key] < 0 else ""
    return row


def investor_value_from_krx_row(row: dict[str, Any], labels: tuple[str, ...]) -> int | None:
    investor_text = " ".join(str(row.get(key, "")) for key in ("INVST_TP_NM", "INVST_TP_CD", "INVST_NM", "TRD_NM"))
    for label in labels:
        if label and label in investor_text:
            return first_int_from_fields(row, (
                "NET_BUY_TRDVAL",
                "NETBID_TRDVAL",
                "NET_BUY_VAL",
                "NETBID_VAL",
                "ACC_NETBID_TRDVAL",
                "순매수거래대금",
                "순매수",
            ))
    for label in labels:
        value = row.get(label)
        if value is not None:
            return parse_int_value(value)
    return None


def first_int_from_fields(row: dict[str, Any], fields: tuple[str, ...]) -> int | None:
    for field in fields:
        if field in row:
            value = parse_int_value(row[field])
            if value is not None:
                return value
    return None


def parse_int_value(value: Any) -> int | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if not text or text == "-":
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def candidate_market_dates(run_date: str, lookback_days: int = 8) -> list[str]:
    end_date = dt.date.fromisoformat(run_date)
    return [
        (end_date - dt.timedelta(days=offset)).strftime("%Y%m%d")
        for offset in range(lookback_days)
    ]


def safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return round(float(value), 4)
    except (TypeError, ValueError):
        return None


def extract_first(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text, flags=re.DOTALL)
    return html.unescape(match.group(1)) if match else None


def clean_text(text: str) -> str:
    text = re.sub(r"<.*?>", "", text, flags=re.DOTALL)
    return html.unescape(text).strip()


def collect_rss(offline: bool) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    items: list[dict[str, Any]] = []
    quality: list[dict[str, Any]] = []

    if offline:
        return items, [{"source": "rss", "status": "skipped", "reason": "offline mode"}]

    for source, url in RSS_FEEDS:
        try:
            xml_text = fetch_url(url)
            root = ET.fromstring(xml_text)
            for item in root.findall(".//item")[:8]:
                title = item.findtext("title") or ""
                link = item.findtext("link") or ""
                published = item.findtext("pubDate") or ""
                if title:
                    items.append({
                        "source": source,
                        "title": title.strip(),
                        "url": link.strip(),
                        "published_at": published.strip(),
                    })
        except (urllib.error.URLError, ET.ParseError, TimeoutError, Exception) as exc:  # noqa: BLE001
            quality.append({"source": source, "status": "failed", "reason": str(exc)})
    return items, quality


def collect_dart(
    holdings: list[dict[str, Any]],
    run_date: str,
    offline: bool,
    days: int = 7,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if offline:
        return [], [{"source": "dart", "status": "skipped", "reason": "offline mode"}]

    api_key = os.getenv("DART_API_KEY")
    if not api_key:
        return [], [{"source": "dart", "status": "skipped", "reason": "DART_API_KEY not set"}]

    try:
        corp_map = get_dart_corp_map(api_key)
    except Exception as exc:  # noqa: BLE001
        return [], [{"source": "dart", "status": "failed", "reason": f"corp code load failed: {exc}"}]

    end_date = dt.date.fromisoformat(run_date)
    begin_date = end_date - dt.timedelta(days=days)
    disclosures: list[dict[str, Any]] = []
    quality: list[dict[str, Any]] = []

    targets = [
        holding for holding in holdings
        if holding.get("market") == "KR" and int(holding.get("tier", 99)) <= 2
    ]

    for holding in targets:
        stock_code = holding["symbol"]
        dart_stock_code = DART_STOCK_CODE_FALLBACKS.get(stock_code, stock_code)
        corp_code = corp_map.get(dart_stock_code)
        if not corp_code:
            quality.append({
                "source": "dart",
                "symbol": stock_code,
                "name": holding["name"],
                "status": "missing",
                "reason": "corp_code not found",
            })
            continue

        params = {
            "crtfc_key": api_key,
            "corp_code": corp_code,
            "bgn_de": begin_date.strftime("%Y%m%d"),
            "end_de": end_date.strftime("%Y%m%d"),
            "page_count": "20",
        }
        url = f"{DART_API_BASE}/list.json?{urlencode(params)}"
        try:
            payload = json.loads(fetch_url(url))
        except Exception as exc:  # noqa: BLE001
            quality.append({
                "source": "dart",
                "symbol": stock_code,
                "name": holding["name"],
                "status": "failed",
                "reason": str(exc),
            })
            continue

        status = payload.get("status")
        if status == "013":
            continue
        if status != "000":
            quality.append({
                "source": "dart",
                "symbol": stock_code,
                "name": holding["name"],
                "status": "failed",
                "reason": payload.get("message", f"DART status {status}"),
            })
            continue

        for item in payload.get("list", []):
            disclosures.append({
                "source": "dart",
                "symbol": stock_code,
                "dart_stock_code": dart_stock_code,
                "name": holding["name"],
                "corp_code": corp_code,
                "report_name": item.get("report_nm"),
                "receipt_no": item.get("rcept_no"),
                "receipt_date": item.get("rcept_dt"),
                "submitter": item.get("flr_nm"),
                "url": f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={item.get('rcept_no')}",
            })

    return disclosures, quality


def urlencode(params: dict[str, str]) -> str:
    return urllib.parse.urlencode(params)


def get_dart_corp_map(api_key: str) -> dict[str, str]:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / "dart_corp_codes.json"
    if cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8"))

    url = f"{DART_API_BASE}/corpCode.xml?{urlencode({'crtfc_key': api_key})}"
    raw_zip = fetch_bytes(url)
    with zipfile.ZipFile(io.BytesIO(raw_zip)) as archive:
        xml_name = archive.namelist()[0]
        xml_bytes = archive.read(xml_name)

    root = ET.fromstring(xml_bytes)
    mapping: dict[str, str] = {}
    for item in root.findall("list"):
        stock_code = (item.findtext("stock_code") or "").strip()
        corp_code = (item.findtext("corp_code") or "").strip()
        if stock_code and corp_code:
            mapping[stock_code] = corp_code

    cache_path.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")
    return mapping


def build_snapshot(run_date: str, offline: bool) -> dict[str, Any]:
    load_env()
    holdings = read_portfolio()
    us_quotes, us_quality = collect_yfinance(holdings, offline, run_date)
    indicators, indicator_quality = collect_market_indicators(offline, run_date)
    kr_quotes, kr_quality = collect_naver(holdings, offline, run_date)
    krx_quotes, kr_indices, krx_quality = collect_krx_reference(holdings, run_date, offline)
    investor_flows, investor_flow_quality = collect_investor_flows(holdings, run_date, offline)
    rss_news, rss_quality = collect_rss(offline)
    naver_news, naver_news_quality = collect_naver_news(holdings, offline)
    yf_news, yf_news_quality = collect_yfinance_news(holdings, offline)
    disclosures, dart_quality = collect_dart(holdings, run_date, offline)
    news = dedupe_news(rss_news + naver_news + yf_news)

    return {
        "date": run_date,
        "as_of": now_kst().isoformat(),
        "timezone": "Asia/Seoul",
        "portfolio": holdings,
        "market_data": {
            "us_quotes": us_quotes,
            "market_indicators": indicators,
            "kr_quotes": kr_quotes,
            "krx_quotes": krx_quotes,
            "kr_indices": kr_indices,
            "investor_flows": investor_flows,
        },
        "news": news,
        "disclosures": disclosures,
        "macro": {},
        "data_quality": (
            us_quality
            + indicator_quality
            + kr_quality
            + krx_quality
            + investor_flow_quality
            + rss_quality
            + naver_news_quality
            + yf_news_quality
            + dart_quality
        ),
        "notes": [
            "v0.1 collector uses yfinance quotes/news, Naver Finance prices, Naver Search news, CNBC RSS, KRX Open API with pykrx fallback, and DART when DART_API_KEY is set.",
            "FRED and ECOS collectors are planned next.",
        ],
    }


def dedupe_news(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in items:
        key = item.get("url") or f"{item.get('source')}:{item.get('symbol')}:{item.get('title')}"
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def write_news_markdown(path: Path, snapshot: dict[str, Any]) -> None:
    lines = [f"# News Input - {snapshot['date']}", ""]
    if not snapshot["news"]:
        lines.append("No RSS news items collected.")
    for item in snapshot["news"]:
        lines.append(f"- [{item['source']}] {item['title']}")
        if item.get("published_at"):
            lines.append(f"  - Published: {item['published_at']}")
        if item.get("url"):
            lines.append(f"  - URL: {item['url']}")
    lines.append("")
    lines.append("## Data Quality")
    for quality in snapshot["data_quality"]:
        lines.append(f"- {quality}")
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=now_kst().date().isoformat())
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args(argv)

    out_dir = INCOMING_DIR / args.date
    out_dir.mkdir(parents=True, exist_ok=True)
    snapshot = build_snapshot(args.date, args.offline)

    source_path = out_dir / "source.json"
    news_path = out_dir / "news.md"
    source_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    write_news_markdown(news_path, snapshot)

    print(f"wrote {source_path}")
    print(f"wrote {news_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
