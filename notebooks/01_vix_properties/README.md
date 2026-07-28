# VIX Analysis

This track validates VIX distribution properties and the VIX component of the
composite market-risk indicator. Trading entries and portfolio rules remain in
the separate VIX event-strategy track.

## Current notebook

[`vix_distribution_analysis.ipynb`](vix_distribution_analysis.ipynb) follows
the same research presentation as the SKEW validation notebook:

- compares Raw VIX and Log VIX using daily Close observations;
- reuses the existing strategy's relative stress-event classification;
- separates event-driven right-tail observations from ordinary daily states;
- tests whether non-event daily Log VIX is approximately normal;
- measures the change in stress-event frequency before and after 2008;
- distinguishes a change in event occupancy from a permanent shift in the
  ordinary VIX center;
- applies the same current-inclusive two-stage 120-month rolling calculation
  used by the SKEW component;
- interprets the final normal-CDF value as a bounded relative score, not a
  calibrated probability or empirical percentile.

Daily Close is the primary distribution series because it preserves the time
spent at each VIX level. Monthly Close is used only for the composite model's
ten-year rolling parameter. Monthly High remains part of the separate event
classification methodology, not the descriptive VIX-level distribution.
High and Close are validated independently, so an invalid High cannot remove a
valid Close from the distribution or rolling calculation.

## Research interpretation

The working model separates the observed VIX distribution into:

1. an ordinary-state daily Log VIX distribution that is materially closer to
   normal than Raw VIX;
2. a stress-event component that creates much of the full distribution's right
   tail;
3. persistent high- and low-volatility states that change the recent mixture
   of ordinary and event observations.

The rolling calculation intentionally retains event observations. Its purpose
is to evaluate the current monthly VIX Close relative to the level, dispersion,
event frequency, event magnitude, and state persistence observed over the
trailing ten years.

## Boundary

The distribution notebook validates measurement and interpretation. It does
not redefine the VIX event strategy, trading entries, leverage, portfolio
accounting, or forward-return tests.

The frozen numerical results and research decision are recorded in
[`docs/validation/vix-distribution-and-risk-parameter.md`](../../docs/validation/vix-distribution-and-risk-parameter.md).
