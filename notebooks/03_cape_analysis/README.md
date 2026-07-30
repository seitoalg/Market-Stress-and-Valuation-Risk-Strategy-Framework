# Shiller CAPE Analysis

This track validates Shiller CAPE as the valuation component of the composite
market-risk indicator. It follows the research presentation used by the VIX
and SKEW validation tracks, while keeping trading rules and composite-strategy
tests outside the analysis.

## Scope

The analysis answers four separate questions:

1. What are the distributional and time-series properties of Raw CAPE?
2. Does CAPE contain a long-run structural trend that makes an absolute
   full-history threshold misleading?
3. Does the approved two-stage 120-month transformation produce a stable and
   interpretable relative-valuation measure?
4. How should the final Z-score and normal-CDF output be interpreted inside the
   composite indicator?

The notebook must separate descriptive evidence from the official parameter
decision. Alternative trend models are diagnostics, not automatically adopted
transformations.

## Executable notebook

`cape_distribution_analysis.ipynb` uses visible Markdown, code, result tables,
and chart cells in the following order.

### 1. Research boundary and definitions

- Define Shiller CAPE as price divided by the trailing ten-year average of real
  earnings.
- State that high relative CAPE represents higher valuation risk.
- State that the notebook validates measurement, not market timing.
- Exclude forward returns, drawdowns, entries, exits, staged profit-taking, and
  composite alert rules.

### 2. Data acquisition and preparation

- Download the full monthly CAPE table from Multpl.
- Parse dates and numeric values visibly.
- Sort chronologically.
- Deduplicate multiple observations in the same calendar month, retaining the
  latest observation.
- Keep completed months in the historical distribution.
- Treat the latest incomplete month as a provisional current input.
- Display source URL, sample dates, observation count, missing values, and
  duplicate-month diagnostics.

### 3. Raw CAPE distribution

- Display the full-sample histogram and empirical CDF without arbitrary era
  partitions.
- Report count, mean, median, standard deviation, minimum, maximum, skewness,
  excess kurtosis, and serial dependence.
- Display a normal Q-Q plot only as a diagnostic.
- Record the current Raw CAPE percentile.
- Explain why the raw full-history percentile can classify the modern market
  as persistently expensive when the center of CAPE has moved over time.

### 4. Long-run level and trend diagnostics

- Aggregate monthly CAPE into annual mean and annual median series.
- Display both annual series through the full sample.
- Estimate simple log-linear trends for transparency.
- Report annualized trend estimates and fit diagnostics.
- Do not select a fixed exponential correction merely because it improves the
  histogram.

### 5. Why the rolling window is 120 months

- Connect the 120-month reference window to CAPE's own trailing ten-year real
  earnings denominator.
- Treat ten years as an economically specified horizon, not a window selected
  by maximizing backtest performance.
- Explain that the first and second rolling stages require roughly twenty years
  of history before the first final Z-score is available.

### 6. Official two-stage CAPE transformation

The canonical parameter is:

1. calculate the trailing 120-month CAPE mean;
2. calculate relative deviation:
   `(CAPE - trailing mean) / trailing mean`;
3. calculate the trailing 120-month mean and sample standard deviation of that
   deviation;
4. standardize the current deviation:
   `(deviation - trailing deviation mean) / trailing deviation std`;
5. map the Z-score through the standard-normal CDF.

The notebook must display every intermediate column for the latest observation.
CAPE itself is not log-transformed in the official calculation.

### 7. Interpretation of the two stages

- Stage one asks how far current CAPE is from its own trailing ten-year level.
- Stage two asks how unusual that relative deviation is compared with the
  trailing ten-year distribution of deviations.
- Describe the result as a local standardized deviation or "deviation of the
  deviation."
- Describe the normal CDF as the bounded theoretical cumulative probability
  corresponding to the Z-score.
- Show its exact sigma correspondence, including `+1 sigma = 84.13%` and
  `+2 sigma = 97.72%`.

### 8. Final Z-score validation

- Report the final Z-score's mean, standard deviation, skewness, excess
  kurtosis, and lag-1 autocorrelation.
- Compare empirical frequencies inside `+/-1`, `+/-2`, and `+/-3` Z units with
  standard-normal frequencies.
- Report upper and lower one-sided exceedance frequencies separately.
- Display a histogram and normal Q-Q plot.
- Run normality tests as descriptive diagnostics while acknowledging serial
  dependence.
- State clearly that Z remains meaningful as a local distance even when its
  pooled distribution is not `N(0,1)`.

### 9. Implementation verification and current reading

- Display latest date and Raw CAPE.
- Display trailing CAPE mean and relative deviation.
- Display trailing deviation mean and standard deviation.
- Display final Z-score and bounded normal score.
- Display the empirical rank of the final Z separately from the normal score.
- State whether the latest month is completed or provisional.
- Confirm current-inclusive rolling-window behavior.
- Confirm that the calculation uses sample standard deviation consistently.
- Verify that duplicate current-month rows cannot enter the model twice.
- Confirm that all historical values used on a date were available on that
  date.

### 10. Decision and limitations

- State whether the approved 120-month two-stage transformation is retained.
- List the economic rationale, statistical evidence, and known distortions
  separately.
- Record that the output measures relative valuation risk.

## Official CAPE parameter

The working parameter remains:

1. Raw monthly CAPE;
2. relative deviation from the trailing 120-month CAPE mean;
3. rolling standardization of that deviation over 120 months;
4. standard-normal CDF mapping to a bounded 0-1 valuation-risk score.

The 120-month choice is justified primarily by alignment with CAPE's own
ten-year real-earnings construction. Distributional diagnostics support the
interpretation but do not define the window.

## Shared implementation

The canonical calculation lives in `src/market_risk/cape.py`. The CAPE
validation notebook and integrated composite notebook import that same
function so the research and production calculations cannot diverge.
