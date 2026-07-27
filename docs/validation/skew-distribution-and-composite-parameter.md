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
