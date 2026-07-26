# Research Roadmap

## 1. VIX properties

- Compare raw and log-transformed VIX distributions.
- Evaluate central fit and tail deviations with histograms and Q-Q plots.
- Compare daily Close and monthly High.
- Examine regime stability and adaptive thresholds.

## 2. SKEW analysis

- Study the SKEW distribution and structural trend.
- Test VIX-SKEW state combinations.
- Measure forward returns, drawdowns, and stress-event timing.
- Separate descriptive relationships from predictive evidence.

## 3. Market risk indicator

- Maintain interpretable VIX, SKEW, and Shiller CAPE components.
- Define the composite as a relative risk percentile, not a crash probability.
- Evaluate correlation, information overlap, horizons, and calibration.

## 4. VIX event strategy

- Reconstruct month-to-date VIX High on a point-in-time basis.
- Preserve the long-run backfilled baseline as a retrospective classification choice.
- Add staged entries, profit-taking, cash management, and daily portfolio accounting.
- Compare against SPY, QQQ, periodic investment, and continuous leverage.
- Test whether event-conditioned leverage improves the risk-return trade-off.

## Development principles

- Preserve the original notebooks in Git history.
- Make one methodological change per commit when practical.
- Separate descriptive analysis, event study, and executable backtest results.
- Record assumptions, limitations, and robustness checks.
- Move reusable calculations from notebooks into `src/` over time.
