# SKEW Analysis

This track validates SKEW as one input to the composite market-risk
indicator. It does not define a standalone SKEW trading event or strategy.

## Current notebook

[`skew_distribution_analysis.ipynb`](skew_distribution_analysis.ipynb) follows
the same research presentation used by the VIX distribution notebook:

- states the analytical scope and interpretation boundary in Markdown;
- downloads and prepares the source data in visible cells;
- compares raw and log SKEW Close distributions;
- separates daily observations from completed-month observations;
- displays descriptive statistics and serial dependence;
- presents histograms and Q-Q plots;
- compares broad market regimes;
- displays the exact current-inclusive two-stage rolling Z transformation used
  by the composite indicator;
- uses the shared implementation in `src/market_risk/skew.py`, which also
  supplies the SKEW component in the composite notebook;
- keeps the incomplete current month out of the historical monthly
  distribution while retaining it as a provisional current model input.

The notebook retains its latest validated result tables and displays committed
chart snapshots from `reports/generated/skew_distribution/`. Rerunning all
cells regenerates the live tables and Matplotlib charts; Git history preserves
earlier research snapshots.

## Official SKEW parameter

The implemented parameter is only the approved two-stage transformation:

1. log SKEW;
2. relative deviation from the trailing 120-month log mean;
3. rolling standardization of that deviation over 120 months;
4. standard-normal CDF mapping to a bounded 0–1 composite score.

The result is a bounded normal-score mapping. It is not a crash probability or
an empirical historical percentile.

## Boundary

Forward returns, drawdowns, joint VIX-SKEW event states, and trading rules are
outside this stage. Those tests should only follow after the SKEW parameter
transformation has been validated.
