# KSS

KSS is a Korean equity quantitative valuation engine for KOSPI and KOSDAQ stocks.

The v1 scope focuses on deterministic valuation logic:

- financial vs non-financial company classification support
- peer group selection for the 3 most comparable companies
- fair value band calculation
- final verdict and confidence calculation
- value-trap risk detection

Product requirements are defined in `PRD.md`.

## Development

```bash
python -m pytest
```

