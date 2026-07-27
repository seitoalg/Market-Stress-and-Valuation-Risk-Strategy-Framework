# Market Stress and Valuation Risk Strategy Framework

A Python research portfolio studying how market stress, option-implied tail risk, and valuation conditions can be translated into interpretable risk indicators and event-driven allocation rules.

The repository is designed as a research program rather than a single trading model. Descriptive distribution analysis, indicator construction, event detection, and executable backtesting are kept separate so that statistical observations are not presented as predictive evidence without validation.

## Research status

| Research track | Status | Current output |
|---|---|---|
| **VIX properties** | Descriptive baseline completed | Compares raw and log-transformed VIX distributions, tail behavior, monthly highs, Q-Q behavior, and regime stability. |
| **SKEW analysis** | Planned / partially integrated | Dedicated analysis will test structural trends, VIX-SKEW joint states, forward outcomes, and incremental information beyond VIX. |
| **Market risk indicator** | Prototype completed | Combines VIX complacency risk, SKEW tail-risk pricing, and Shiller CAPE valuation risk into an equal-weighted relative percentile. |
| **VIX event strategy** | Event engine completed; backtest in progress | Detects stress events and staged entries using point-in-time monthly VIX highs. Portfolio accounting, exits, transaction assumptions, and benchmark comparison remain in development. |

## Main findings so far

### VIX distribution

- Raw VIX is strongly right-skewed and heavy-tailed.
- The log transformation substantially improves central distributional fit and reduces skewness and excess kurtosis.
- Log VIX is still not fully normal because tail events and regime dependence remain economically important.
- Monthly VIX High is useful as a stress-state variable, but distributional fit alone does not establish a profitable strategy.

### Point-in-time event validation

The VIX event engine was rebuilt so that each historical day uses only the current month-to-date VIX High, rather than the finalized monthly High that became known later.

In the controlled comparison:

- stress-event count was unchanged;
- entry-signal count was unchanged;
- event dates, signal dates, and wave counts were unchanged;
- no daily +2 sigma classifications changed.

The correction improves chronological accuracy without changing the historical experimental conclusion. See [Point-in-Time Monthly VIX High Validation](docs/validation/point-in-time-monthly-high.md).

### Composite market risk indicator

The composite indicator is an interpretable **relative risk percentile**, not a crash probability or a market-timing forecast.

- Low VIX is treated as higher complacency risk.
- High SKEW is treated as higher option-implied tail-risk pricing.
- High Shiller CAPE is treated as higher valuation risk.
- The current prototype equal-weights the three components.

Predictive validity, information overlap, weighting alternatives, calibration, and regime robustness have not yet been established.

## Repository layout

- `notebooks/01_vix_properties/` — VIX distribution and regime research.
- `notebooks/02_skew_analysis/` — dedicated SKEW research track.
- `notebooks/03_market_risk_indicator/` — composite VIX, SKEW, and CAPE indicator.
- `notebooks/04_vix_event_strategy/` — point-in-time stress-event detection and staged-entry research.
- `src/` — reusable calculations as notebook logic is refactored.
- `tests/` — planned tests for indicators, signals, and portfolio accounting.
- `reports/` — selected figures and result tables as they are separated from notebooks.
- `docs/` — methodology, assumptions, validation notes, roadmap, and research decisions.

See [the research roadmap](docs/research-roadmap.md) and [the original import manifest](docs/original-import-manifest.md).

## Development stage

### Completed

- Organized the original notebooks into separate research tracks.
- Preserved the original research state through Git history and an import manifest.
- Separated descriptive VIX research from event-strategy rules.
- Reconstructed monthly VIX High on a point-in-time basis.
- Documented the controlled point-in-time validation.
- Standardized English documentation and notebook comments.
- Pinned the Python version and research dependencies.
- Added shared UTC run timestamps and source observation-date reporting.

### In progress

- Refactoring reusable calculations from notebooks into `src/`.
- Adding tests for indicators, event states, entry timing, and look-ahead prevention.
- Completing portfolio accounting, cash management, exits, and transaction assumptions.
- Comparing the event strategy with SPY, QQQ, periodic investment, and continuous leverage.
- Separating representative charts and result tables into `reports/`.

### Planned

- Dedicated SKEW distribution and forward-outcome research.
- Correlation and information-overlap analysis across VIX, SKEW, and CAPE.
- Alternative composite weights and calibration tests.
- Regime, rolling-window, and out-of-sample robustness checks.
- Risk-adjusted performance reporting, including drawdown and benchmark analysis.

## Live data and reproducibility

The notebooks are designed to refresh from live public market-data sources. Each full execution records one UTC run timestamp and reports the latest observation date used for each source.

Notebook outputs are committed research snapshots. Because code and methodology can be updated before every notebook is re-executed, always check the printed run timestamp and source dates inside the notebook before treating saved output as current.

For consistent execution:

1. Use Python 3.13.9.
2. Install the pinned dependencies with `python -m pip install -r requirements.txt`.
3. Run each notebook from top to bottom with **Run All**.
4. Confirm that all source dates, tables, and charts were generated during the same run.
5. Commit the refreshed notebook only after the full execution completes successfully.

Primary live sources currently include Cboe VIX history, Yahoo Finance data accessed through `yfinance`, and the Shiller CAPE table from Multpl.

## Research principles

- Distinguish descriptive relationships from predictive evidence.
- Prevent look-ahead bias by reconstructing the historical information set.
- State retrospective assumptions explicitly when full point-in-time reconstruction is unavailable.
- Make methodological changes traceable through focused Git commits.
- Report null or unchanged results rather than optimizing them away.
- Treat robustness, benchmarks, transaction assumptions, and portfolio accounting as required parts of strategy evaluation.

## Limitations

This repository is an active research portfolio. Several components remain prototypes, and the event strategy is not yet a complete executable backtest. Public data sources may also revise historical observations or change their delivery format.

Nothing in this repository is investment advice or a recommendation to trade any security or strategy.
