# SKEW Distribution and Composite-Parameter Validation

Date: 2026-07-26

## Scope

This validation treats SKEW as one parameter of the composite market-risk
indicator. It does not define SKEW events, trading entries, forward returns, or
drawdown rules.

The analysis uses Yahoo Finance `^SKEW` Close observations from 1990-01-02
through 2026-07-24. Historical monthly distribution tests include completed
months only, through 2026-06-30. The 2026-07-24 Close is used separately as the
provisional July model input.

The executable analysis and its saved result tables are presented in
`notebooks/02_skew_analysis/skew_distribution_analysis.ipynb`, following the
same notebook-based research format as the VIX distribution analysis.

## Raw and log distributions

| Series | N | Skewness | Excess kurtosis | Lag-1 autocorrelation |
|---|---:|---:|---:|---:|
| Raw daily Close | 9,133 | 1.284 | 1.576 | 0.963 |
| Log daily Close | 9,133 | 1.046 | 0.772 | 0.962 |
| Raw completed-month Close | 438 | 1.285 | 1.194 | 0.853 |
| Log completed-month Close | 438 | 1.079 | 0.587 | 0.851 |

Log transformation reduces right skew and excess kurtosis, but it does not
make the full-history daily or monthly series normal. Shapiro-Wilk and
Jarque-Bera tests reject normality for all four full-history series.

The observations are also strongly serially dependent. Normality-test p-values
therefore should be treated as descriptive diagnostics rather than IID
inference.

## Structural regimes

The log completed-month Close is materially closer to a symmetric distribution
within broad regimes:

| Regime | N | Mean log SKEW | Std | Skewness | Jarque-Bera p |
|---|---:|---:|---:|---:|---:|
| 1990-2007 | 216 | 4.748 | 0.041 | 0.365 | 0.087 |
| 2008-2019 | 144 | 4.816 | 0.067 | 0.475 | 0.066 |
| 2020-2026-06 | 78 | 4.944 | 0.091 | -0.434 | 0.246 |

The larger full-sample non-normality is therefore driven substantially by
structural movement in the level and volatility of SKEW. A stationary
full-history lognormal model is not supported.

## Financial-crisis trend test

The broad regime comparison is supplemented with a segmented trend analysis of
completed-month Log SKEW. January 2008 is selected **a priori** from financial
history and then tested; it is not a breakpoint chosen by searching for the
date that maximizes statistical significance.

Because monthly SKEW is strongly serially dependent, the trend p-values use
Newey-West/HAC standard errors with 12 lags.

| Period | N | Annualized Log SKEW trend | HAC p-value | Interpretation |
|---|---:|---:|---:|---|
| 1990-2007 | 216 | +0.17% | 0.102 | approximately horizontal |
| 2008-2026-06 | 222 | +1.31% | 6.79e-15 | strongly significant upward trend |

The HAC p-value for the change in slope at the 2008 split is 8.74e-09.
Therefore, the evidence supports treating the pre-crisis period as
approximately horizontal and the post-crisis period as a structurally rising
Log SKEW regime.

An earlier exploratory endpoint produced an annualized post-2008 estimate of
about 1.26%. Updating the completed-month sample through June 2026 gives about
1.31%; the economic and statistical conclusion is unchanged.

This confirms a parameter change at the historically specified 2008 boundary.
It does not claim that an unrestricted breakpoint search proved January 2008
to be the unique exact break date.

## Why the rolling window is 120 months

Monthly SKEW has strong persistence: its lag-1 autocorrelation is approximately
0.85. A short rolling window would allow a sustained risk elevation to reset
its own baseline too quickly. Conversely, a much longer window would adapt too
slowly to the post-crisis structure and would sharply reduce the usable
transformed sample.

A 120-month window is therefore retained as a practical balance among:

- stability against short-lived and serially correlated movements;
- adaptation to the post-crisis structural regime;
- preservation of a usable number of transformed observations.

The persistence analysis supports ten years as a practical design range. It
does not make 120 months a uniquely determined mathematical optimum.

## Why the transformation has two stages

The first stage measures the relative deviation of Log SKEW from its trailing
120-month mean. This removes the evolving **level** represented by the
post-crisis upward trend.

A level adjustment alone is insufficient because the distribution's
dispersion also changed. The standard deviation of completed-month Log SKEW
rose from approximately 0.041 in 1990-2007 to 0.091 from 2020 onward. The
second stage therefore standardizes the first-stage deviation using the
rolling mean and rolling standard deviation of that deviation.

The two stages have different jobs:

1. stage one removes the evolving structural level;
2. stage two evaluates the residual deviation relative to its evolving center
   and variability.

The normal CDF then converts the resulting Z-score into the bounded component
required by the composite indicator. This design intentionally measures an
unusual move relative to the current SKEW structure rather than the absolute
historical height of SKEW. Whether that removes too much persistent economic
risk remains a question for later forward-return and drawdown validation.

## Current composite-model transformation

The live composite model applies:

1. log SKEW;
2. deviation from the trailing 120-month log mean;
3. a second 120-month rolling mean and standard deviation of that deviation;
4. a normal CDF mapping of the resulting Z-score.

Across the 201 available transformed observations, the Z-score has:

- mean 0.367;
- standard deviation 1.212;
- skewness -0.241;
- excess kurtosis -0.199;
- lag-1 autocorrelation 0.591.

Shapiro-Wilk and Jarque-Bera do not reject the shape of a normal distribution
at the 5% level. However, the series is not calibrated as standard normal:
the Kolmogorov-Smirnov p-value against N(0,1) is 0.000022. Consequently, the
normal-CDF output is not a historically calibrated percentile and should be
described as a bounded normal-score mapping.

## Current reading

Using the 2026-07-24 SKEW Close of 147.28, the approved two-stage model gives:

- Z-score: 0.131;
- bounded normal-score: 55.19%.

This means the current deviation is only modestly above the model's rolling
center after the post-crisis structural rise in SKEW has been absorbed. The
55.19% result is neither a crash probability nor an empirical rank among the
past 120 months.

## Decision

The composite indicator retains the current-inclusive two-stage 120-month
rolling transformation:

1. log SKEW;
2. relative deviation from its rolling log mean;
3. rolling mean and standard deviation of that deviation;
4. normal-CDF mapping of the resulting Z-score.

This transformation materially absorbs the structural rise in SKEW while
preserving unusually large deviations as the risk signal. The observed
post-transformation mean of 0.367 and standard deviation of 1.212 are not
recentered or rescaled at this stage.

The normal-CDF result is used as a bounded composite risk score, not as a
calibrated crash probability or historical percentile. Trading thresholds,
event rules, and forward-return analysis remain outside this validation.

The canonical calculation is `src/market_risk/skew.py`. Both the SKEW
validation notebook and the integrated composite notebook use that shared
implementation.
