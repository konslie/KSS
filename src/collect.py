from __future__ import annotations

import argparse
import datetime as dt
import html
import io
import json
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


def collect_yfinance(holdings: list[dict[str, Any]], offline: bool) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
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
        row, error = fetch_yfinance_quote(yf, symbol)
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


def collect_market_indicators(offline: bool) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    quality: list[dict[str, Any]] = []

    if offline:
        return rows, [{"source": "yfinance_indicators", "status": "skipped", "reason": "offline mode"}]

    try:
        import yfinance as yf  # type: ignore
    except ImportError:
        return rows, [{"source": "yfinance_indicators", "status": "failed", "reason": "package not installed"}]

    for symbol, name in MARKET_INDICATORS.items():
        row, error = fetch_yfinance_quote(yf, symbol)
        if row:
            row["name"] = name
            rows.append(row)
        if error:
            error["source"] = "yfinance_indicators"
            quality.append(error)
    return rows, quality


def fetch_yfinance_quote(yf: Any, symbol: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    try:
        ticker = yf.Ticker(symbol)
        history = ticker.history(period="10d", interval="1d", auto_adjust=False)
        if history.empty:
            return None, {"source": "yfinance", "symbol": symbol, "status": "missing", "reason": "empty history"}
        last = history.iloc[-1]
        previous = history.iloc[-2] if len(history) > 1 else None
        close = float(last["Close"])
        previous_close = float(previous["Close"]) if previous is not None else None
        change = None if previous_close is None else close - previous_close
        change_pct = None if previous_close in (None, 0) else ((close - previous_close) / previous_close) * 100
        recent_closes = [round(float(value), 4) for value in history["Close"].tail(7)]
        return {
            "symbol": symbol,
            "source": "yfinance",
            "close": round(close, 4),
            "previous_close": round(previous_close, 4) if previous_close is not None else None,
            "change": round(change, 4) if change is not None else None,
            "change_pct": round(change_pct, 2) if change_pct is not None else None,
            "recent_closes": recent_closes,
            "volume": int(last["Volume"]) if "Volume" in last else None,
        }, None
    except Exception as exc:  # noqa: BLE001
        return None, {"source": "yfinance", "symbol": symbol, "status": "failed", "reason": str(exc)}


def collect_naver(holdings: list[dict[str, Any]], offline: bool) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
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
                history, history_error = fetch_yfinance_quote(yf, kr_yfinance_symbol(symbol))
                if history and history.get("recent_closes"):
                    row["recent_closes"] = history["recent_closes"][:-1] + ([current_price] if current_price is not None else [])
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


def collect_pykrx(
    holdings: list[dict[str, Any]],
    run_date: str,
    offline: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    stock_rows: list[dict[str, Any]] = []
    index_rows: list[dict[str, Any]] = []
    quality: list[dict[str, Any]] = []

    if offline:
        return stock_rows, index_rows, [{"source": "pykrx", "status": "skipped", "reason": "offline mode"}]

    if not os.getenv("KRX_ID") or not os.getenv("KRX_PW"):
        return stock_rows, index_rows, [{"source": "pykrx", "status": "skipped", "reason": "KRX_ID or KRX_PW not set"}]

    try:
        import pandas as pd  # type: ignore
        from pykrx import stock  # type: ignore
    except ImportError:
        return stock_rows, index_rows, [{"source": "pykrx", "status": "failed", "reason": "package not installed"}]

    dates = candidate_market_dates(run_date)
    domestic_names = {
        holding["symbol"]: holding["name"]
        for holding in holdings
        if holding.get("market") == "KR"
    }

    try:
        ohlcv = None
        used_date = None
        for date in dates:
            frames = [
                stock.get_market_ohlcv_by_ticker(date, market="KOSPI"),
                stock.get_market_ohlcv_by_ticker(date, market="KOSDAQ"),
            ]
            candidate = pd.concat(frames)
            if has_columns(candidate, ["종가"]):
                ohlcv = candidate
                used_date = date
                break
        if ohlcv is None:
            quality.append({"source": "pykrx", "status": "unavailable", "reason": "no usable stock ohlcv returned"})
        else:
            for symbol, name in domestic_names.items():
                if symbol not in ohlcv.index:
                    quality.append({"source": "pykrx", "symbol": symbol, "status": "missing", "reason": "ticker not found"})
                    continue
                row = ohlcv.loc[symbol]
                stock_rows.append({
                    "symbol": symbol,
                    "name": name,
                    "source": "pykrx",
                    "as_of_date": used_date,
                    "price": safe_int(row.get("종가")),
                    "change": safe_int(row.get("대비")),
                    "change_pct": safe_float(row.get("등락률")),
                    "volume": safe_int(row.get("거래량")),
                    "trading_value": safe_int(row.get("거래대금")),
                })
    except Exception as exc:  # noqa: BLE001
        quality.append({"source": "pykrx", "status": "failed", "reason": f"stock ohlcv failed: {exc}"})

    index_specs = [
        ("1001", "KOSPI"),
        ("2001", "KOSDAQ"),
    ]
    for index_code, name in index_specs:
        try:
            frame = None
            used_date = None
            for date in dates:
                candidate = stock.get_index_ohlcv_by_date(date, date, index_code)
                if not candidate.empty and has_columns(candidate, ["종가"]):
                    frame = candidate
                    used_date = date
                    break
            if frame is None:
                quality.append({"source": "pykrx", "index": name, "status": "missing", "reason": "empty index data"})
                continue
            row = frame.iloc[-1]
            index_rows.append({
                "name": name,
                "index_code": index_code,
                "source": "pykrx",
                "as_of_date": used_date,
                "close": safe_float(row.get("종가")),
                "change": safe_float(row.get("등락폭")),
                "change_pct": safe_float(row.get("등락률")),
                "volume": safe_int(row.get("거래량")),
                "trading_value": safe_int(row.get("거래대금")),
            })
        except Exception as exc:  # noqa: BLE001
            quality.append({"source": "pykrx", "index": name, "status": "failed", "reason": str(exc)})

    return stock_rows, index_rows, quality


def candidate_market_dates(run_date: str, lookback_days: int = 8) -> list[str]:
    end_date = dt.date.fromisoformat(run_date)
    return [
        (end_date - dt.timedelta(days=offset)).strftime("%Y%m%d")
        for offset in range(lookback_days)
    ]


def has_columns(frame: Any, columns: list[str]) -> bool:
    return all(column in frame.columns for column in columns)


def safe_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


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
    us_quotes, us_quality = collect_yfinance(holdings, offline)
    indicators, indicator_quality = collect_market_indicators(offline)
    kr_quotes, kr_quality = collect_naver(holdings, offline)
    pykrx_quotes, kr_indices, pykrx_quality = collect_pykrx(holdings, run_date, offline)
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
            "pykrx_quotes": pykrx_quotes,
            "kr_indices": kr_indices,
        },
        "news": news,
        "disclosures": disclosures,
        "macro": {},
        "data_quality": (
            us_quality
            + indicator_quality
            + kr_quality
            + pykrx_quality
            + rss_quality
            + naver_news_quality
            + yf_news_quality
            + dart_quality
        ),
        "notes": [
            "v0.1 collector uses yfinance quotes/news, Naver Finance prices, Naver Search news, CNBC RSS, pykrx, and DART when DART_API_KEY is set.",
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
