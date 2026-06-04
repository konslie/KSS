# Morning Investment Briefing

Personal morning investment briefing pipeline.

## v0.1 Flow

```text
Codex Automation at 08:00 KST
  -> make collect
  -> read data/incoming/YYYY-MM-DD/source.json and news.md
  -> write data/reports/YYYY-MM-DD/final.md
  -> make render-html
  -> commit and push docs/index.html through the configured GitHub Pages repo
```

## Local Checks

```bash
make collect-offline
make test
```

## GitHub Pages Setup

Configure GitHub Pages to serve the `docs/` directory from the main branch. The renderer writes:

```text
docs/index.html
docs/reports/YYYY-MM-DD.html
```

After connecting this directory to a GitHub repository:

```bash
git add .
git commit -m "Add morning investment briefing automation"
git push
```

Then enable GitHub Pages with:

```text
Settings -> Pages -> Build and deployment -> Deploy from a branch -> main / docs
```

## Optional Data Sources

- `yfinance` improves US stock and ETF collection when installed.
- yfinance also collects market indicators: KOSPI, KOSDAQ, Nasdaq, S&P 500, VIX, Gold, USD/KRW, Philadelphia Semiconductor Index.
- yfinance also collects overseas holding news.
- Naver Finance is fetched with a lightweight HTML parser for Korean prices.
- Naver Search API collects Korean holding-specific news when `NAVER_CLIENT_ID` and `NAVER_CLIENT_SECRET` are set.
- `pykrx` can add Korean stock fallback data and KOSPI/KOSDAQ index data only when local KRX credentials are available.
- CNBC RSS is fetched with Python standard library XML parsing for global market context.
- DART disclosures are collected when `DART_API_KEY` is set.
- Preferred shares use common-stock DART lookup fallbacks where needed.

## Local Secrets

Do not commit API keys. Put local keys in `.env`:

```bash
DART_API_KEY=your_key_here
NAVER_CLIENT_ID=your_client_id_here
NAVER_CLIENT_SECRET=your_client_secret_here
```

The collector skips DART and records `DART_API_KEY not set` when the key is missing.

`pykrx` is optional. Without local `KRX_ID` and `KRX_PW`, it is skipped because the installed version requires KRX login in this environment.
