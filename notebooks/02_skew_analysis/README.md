# SKEW Analysis

This track validates SKEW as one input to the composite market-risk
indicator. It does not define a standalone SKEW trading event or strategy.

## Current scope

`skew_distribution_analysis.py`:

- compares raw and log SKEW Close distributions;
- separates daily observations from completed-month observations;
- checks Q-Q behavior and broad regime stability;
- reports serial dependence so normality-test p-values are not treated as IID
  evidence;
- reproduces and tests the two-stage rolling Z transformation currently used
  by the composite indicator;
- uses the shared implementation in `src/market_risk/skew.py`, which also
  supplies the SKEW component in the composite notebook;
- keeps the incomplete current month out of the historical monthly
  distribution while retaining it as a provisional current model input.

Generated tables and figures are written to
`reports/generated/skew_distribution/`.

## Boundary

Forward returns, drawdowns, joint VIX-SKEW event states, and trading rules are
outside this stage. Those tests should only follow after the SKEW parameter
transformation has been validated.
