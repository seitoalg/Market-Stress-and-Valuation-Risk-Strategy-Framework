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

## Live data and reproducibility

The notebooks are designed to refresh from the latest available market data. Each full execution records a single UTC run timestamp and reports the latest observation date for every source. Saved outputs therefore represent the most recent committed run, while Git history preserves earlier snapshots.

For consistent results:

1. Use Python 3.13.9.
2. Install the pinned dependencies with `python -m pip install -r requirements.txt`.
3. Run each notebook from top to bottom with **Run All**.
4. Commit the refreshed notebook only after all tables and charts were generated in that same run.

Primary live sources currently include Cboe VIX history, Yahoo Finance data accessed through yfinance, and the Shiller CAPE table from Multpl.