# Shiller CAPE Distribution and Composite-Parameter Validation

Status: retained with interpretation limits.

## Scope

This validation treats Shiller CAPE as the valuation component of the
composite market-risk indicator. It validates measurement and interpretation,
not trading rules, forward returns, drawdowns, or portfolio actions.

## Data

The executable notebook retrieved the Multpl monthly Shiller PE table on
2026-07-30. After calendar-month deduplication, the sample contained 1,866
observations from 1871-02-01 through 2026-07-29. Two source rows belonged to a
duplicate calendar month; the latest dated row was retained. There were no
missing calendar months in the resulting series.

The 2026-07-29 observation is a provisional current-month value. It is shown
separately from the completed history and is permitted as the current live
input.

## Raw CAPE distribution

Raw CAPE had a mean of 17.3996, median of 16.1100, standard deviation of
7.4877, skewness of 1.0547, and excess kurtosis of 1.0663. The range was 4.78
to 44.19. Lag-1 monthly autocorrelation was 0.9954.

The current raw CAPE of 39.93 ranked at the 98.77th percentile of the full
history. That result is descriptively correct but is not sufficient for the
live risk score: the full-history distribution combines very different
valuation levels and makes a structurally higher modern regime appear
persistently expensive.

## Long-run trend evidence

Separate log-linear fits to annual mean and annual median CAPE both showed
positive historical drift. The annualized estimates were 0.4465% for the mean
and 0.4480% for the median; both had an R-squared near 0.232.

This establishes that absolute levels are not stable through the full sample,
but it does not justify subtracting one retrospectively fitted exponential
trend in production. Such a fit uses the final sample endpoint and imposes one
constant growth rate across the entire history. It remains a diagnostic, not
the official correction.

## Why the rolling window is 120 months

The primary rationale is economic alignment. CAPE already averages real
earnings over ten years, so the valuation reference and deviation-distribution
reference use the same pre-specified horizon.

This is not a claim that CAPE has an exact ten-year cycle or that 120 months is
the statistically unique optimum. Because the two rolling stages are
sequential, the first final Z-score requires 239 monthly observations.

## Official two-stage transformation

For monthly CAPE `CAPE_t`:

```text
CAPE_Mean_120_t = mean(CAPE, trailing 120 months)
Deviation_t = (CAPE_t - CAPE_Mean_120_t) / CAPE_Mean_120_t
Deviation_Mean_120_t = mean(Deviation, trailing 120 months)
Deviation_Std_120_t = sample_std(Deviation, trailing 120 months)
Z_t = (Deviation_t - Deviation_Mean_120_t) / Deviation_Std_120_t
Valuation_Risk_t = Normal_CDF(Z_t)
```

Stage one measures CAPE's distance from its trailing level. Stage two measures
how unusual that distance is relative to the trailing distribution of
distances. The calculation uses raw CAPE and current-inclusive windows.

## Final Z-score validation

The final Z series contained 1,628 observations. Its mean was 0.0539,
standard deviation 1.3639, skewness 0.2243, excess kurtosis -0.5654, and lag-1
autocorrelation 0.9836. The Jarque-Bera test rejected exact normality.

| Region | Empirical | Standard normal |
|---|---:|---:|
| Within +/-1 | 50.98% | 68.27% |
| Within +/-2 | 83.97% | 95.45% |
| Within +/-3 | 98.77% | 99.73% |
| Above +1 | 26.60% | 15.87% |
| Above +2 | 10.38% | 2.28% |
| Above +3 | 0.86% | 0.14% |
| Below -1 | 22.42% | 15.87% |
| Below -2 | 5.65% | 2.28% |
| Below -3 | 0.37% | 0.14% |

The pooled series is wider than `N(0,1)`, so its historical exceedance
frequencies differ from the standard-normal reference. The Z-score still has a
valid operational meaning as the current deviation measured in units of its
local rolling standard deviation. The normal CDF preserves the exact
theoretical correspondence: `+1 sigma = 84.13%` and
`+2 sigma = 97.72%`.

High serial dependence is expected because adjacent observations share nearly
all inputs in both 120-month windows. Consequently, 1,628 monthly rows are
enough to characterize the realized score distribution, but they are not
1,628 independent statistical trials.

## Current reading

For the provisional 2026-07-29 observation:

| Quantity | Value |
|---|---:|
| Raw CAPE | 39.9300 |
| Trailing 120-month CAPE mean | 32.3867 |
| Relative deviation | 0.2329 |
| Trailing deviation mean | 0.1944 |
| Trailing deviation sample standard deviation | 0.1191 |
| Final Z-score | 0.3232 |
| Normal-CDF score | 0.6267 |
| Empirical final-Z rank | 0.6100 |

The normal-CDF score and empirical rank are deliberately shown separately.
The first is the common monotonic 0-1 mapping used by the composite indicator;
the second is the observed full-sample rank.

## Decision

Retain the approved two-stage 120-month transformation. Its ten-year horizon
is specified from CAPE's economic construction rather than selected by
backtest optimization, and it converts an unstable absolute valuation level
into an interpretable local relative distance.

Retain the standard-normal CDF as the bounded theoretical cumulative
probability corresponding to each Z-score. Retain Z-based sigma language while
reporting separately that the pooled CAPE Z distribution is wider and more
persistent than a sequence of independent standard-normal draws.
