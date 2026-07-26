# Market Stress and Valuation Risk Strategy Framework

A Python research portfolio examining market stress, option-implied risk, valuation, and event-driven capital allocation.

## Research tracks

1. **VIX properties** — raw and log distributions, tail behavior, regimes, and monthly highs.
2. **SKEW analysis** — distribution, structural trends, interaction with VIX, and forward outcomes.
3. **Market risk indicator** — a composite framework using VIX, SKEW, and Shiller CAPE.
4. **VIX event strategy** — stress-event detection, staged entries, leverage, cash management, and benchmark comparison.

## Repository layout

- `notebooks/01_vix_properties/` — VIX distribution research.
- `notebooks/02_skew_analysis/` — dedicated SKEW research.
- `notebooks/03_market_risk_indicator/` — composite risk indicator research.
- `notebooks/04_vix_event_strategy/` — event detection and strategy research.
- `src/` — reusable research code as notebooks are refactored.
- `tests/` — tests for indicators, signals, and backtests.
- `reports/` — selected figures and result tables.
- `docs/` — methodology, assumptions, roadmap, and research decisions.

## Current stage

The first portfolio commit imports the original notebooks without analytical edits. Subsequent commits will improve point-in-time consistency, reproducibility, portfolio accounting, benchmarks, and robustness while preserving the complete Git history.

See [the research roadmap](docs/research-roadmap.md) and [the original import manifest](docs/original-import-manifest.md).
