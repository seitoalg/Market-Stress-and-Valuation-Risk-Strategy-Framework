# Research Roadmap

## 1. VIX properties

- Compare raw and log-transformed VIX distributions.
- Evaluate central fit and tail deviations with histograms and Q-Q plots.
- Compare daily Close and monthly High.
- Compare distribution stability across market regimes.

## 2. SKEW analysis

- Study the SKEW distribution and structural trend.
- Test VIX-SKEW state combinations.
- Measure forward returns, drawdowns, and stress-event timing.
- Separate descriptive relationships from predictive evidence.

## 3. Shiller CAPE analysis

- Study the full-sample Raw CAPE distribution and long-run level movement.
- Compare transparent trend diagnostics without selecting a retrospective
  fixed-trend correction for live use.
- Validate the two-stage 120-month relative-deviation transformation.
- Connect the window choice to CAPE's own ten-year real-earnings construction.
- Measure final-Z coverage, asymmetry, and serial dependence.
- Interpret the normal CDF as the bounded theoretical cumulative probability
  corresponding to the final Z-score.
- Freeze the CAPE parameter before forward-return or strategy testing.

## 4. Market risk indicator

- Maintain interpretable VIX, SKEW, and Shiller CAPE components.
- Define the composite as a relative risk percentile with transparent
  component context.
- Evaluate correlation, information overlap, horizons, and calibration.

## 5. VIX event strategy

- Define the event threshold from the raw monthly VIX High using a 360-month mean and standard deviation.
- Reconstruct the current month's VIX High on a point-in-time, month-to-date basis.
- Preserve the first completed 360-month baseline as an intentional retrospective classification rule for the early sample.
- Add staged entries, profit-taking, cash management, and daily portfolio accounting.
- Compare against SPY, QQQ, periodic investment, and continuous leverage.
- Test whether event-conditioned leverage improves the risk-return trade-off.

## Development principles

- Preserve the original notebooks in Git history.
- Make one methodological change per commit when practical.
- Separate descriptive analysis, event study, and executable backtest results.
- Record assumptions, limitations, and robustness checks.
- Move reusable calculations from notebooks into `src/` over time.
