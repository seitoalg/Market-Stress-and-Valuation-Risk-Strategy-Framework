# VIX Distribution and Composite-Parameter Validation

Date: 2026-07-28

## Scope

This validation treats VIX in two distinct roles:

1. daily Close describes the distribution of observed VIX levels;
2. monthly Close supplies the VIX parameter in the composite market-risk
   indicator.

Daily High is used only to reproduce the existing VIX strategy's stress-event
classification. The analysis does not redefine the strategy's entries,
position sizing, leverage, or portfolio rules.

The live analysis uses Yahoo Finance `^VIX` observations from 1990-01-02
through 2026-07-27. Historical monthly calculations use completed months
through 2026-06-30, with the 2026-07-27 Close used separately as the
provisional July model input.

High and Close are validated independently. A missing or non-positive High
does not remove an otherwise valid Close from the full distribution or monthly
rolling model. If a valid Close has no corresponding valid High, its event
state is unknown and that observation is excluded only from the
event-versus-ordinary decomposition.

## What the log transformation improves

| Daily Close series | N | Skewness | Excess kurtosis | Shapiro W | KS distance from fitted normal |
|---|---:|---:|---:|---:|---:|
| Raw VIX | 9,208 | 2.210 | 8.746 | 0.833 | 0.109 |
| Log VIX | 9,208 | 0.668 | 0.519 | 0.970 | 0.048 |

Logging VIX materially reduces right skew, excess kurtosis, and the maximum
distance between the empirical CDF and a fitted normal CDF. It therefore
produces a substantially better normal approximation than Raw VIX.

Exact normality is still rejected. Daily Log VIX has lag-1 autocorrelation of
approximately 0.98, so IID normality-test p-values are not a sound pass/fail
criterion by themselves. The improvement is assessed through effect sizes,
histograms, Q-Q plots, and the event decomposition as well as formal tests.

## Event decomposition

The notebook reuses the event strategy's point-in-time rules:

- event entry when daily VIX High exceeds the applicable `+2 sigma` threshold;
- event exit after ten consecutive completed daily High observations below
  `+1 sigma`;
- a 360-month long-run monthly-High baseline;
- retrospective use of the first complete baseline in the early sample;
- after the full window is available, 359 completed monthly highs plus the
  current month-to-date High.

The classifier identifies 12 events and 535 event trading days. Removing those
days changes the distribution as follows:

| Series | N | Skewness | Excess kurtosis | Shapiro W | KS distance from fitted normal |
|---|---:|---:|---:|---:|---:|
| All daily Log VIX | 9,208 | 0.668 | 0.519 | 0.970 | 0.048 |
| Ordinary daily Log VIX | 8,673 | 0.244 | -0.650 | 0.985 | 0.046 |

The ordinary-state Log VIX distribution is much more symmetric. Its lighter
tails explain why the KS distance does not fall as sharply as skewness: event
removal reduces the extreme right tail but leaves a somewhat flat-topped
ordinary-state distribution. It is reasonable to use a normal approximation
for relative measurement, but not to claim an exact Gaussian data-generating
process.

## Nature of the post-2008 change

The detected event rate rises from approximately 0.22 events per year in
1990-2007 to 0.43 per year from 2008 onward.

Daily observations cannot be treated as independent evidence for a change in
the ordinary-state center because VIX is highly persistent. The notebook
therefore compares annual means of ordinary-state Log VIX:

| Period | Annual observations | Mean annual ordinary Log VIX |
|---|---:|---:|
| 1990-2007 | 18 | 2.879 |
| 2008-2026 | 19 | 2.871 |

The post-minus-pre difference is -0.008 log points, equivalent to a geometric
mean ratio of 0.992. Welch's test gives `p = 0.922`, and Mann-Whitney gives
`p = 0.988`.

The evidence therefore does not support a permanent upward shift in the
ordinary-state VIX center at the 2008 boundary. The more relevant structural
change is the increased frequency of transitions into stress events. In the
broader option-market interpretation, this is consistent with a market that
prices and propagates risk more sensitively, especially when considered
alongside the documented upward structural movement in SKEW.

## Why the rolling model retains events

The composite parameter is meant to evaluate the current state of the complete
VIX process, not only its ordinary component. The monthly series therefore
retains event observations. A trailing window can adapt to changes in:

- event frequency;
- event magnitude and duration;
- persistence of high- and low-VIX states;
- the center and dispersion of ordinary observations.

Removing event months would produce a cleaner ordinary-state distribution but
would discard the structural frequency change the parameter is intended to
absorb.

## Current composite-model transformation

The VIX component now uses the same current-inclusive two-stage rolling
operation as SKEW:

1. take Log VIX from monthly Close;
2. calculate
   `(Log VIX - trailing 120-month Log mean) / trailing Log mean`;
3. calculate the trailing 120-month mean and standard deviation of that
   deviation;
4. standardize the current deviation to a Z-score;
5. map the Z-score through the normal CDF.

Because both rolling stages include the current observation, the first valid
Z-score occurs at observation 239. Roughly 20 years of monthly history are
therefore required.

Across 201 available transformed observations, the VIX Z-score has:

- mean 0.058;
- standard deviation 0.982;
- skewness 1.106;
- excess kurtosis 2.257;
- lag-1 autocorrelation 0.772.

The rolling operation does not turn the ordinary/event mixture into a normal
distribution, nor is that its purpose. It expresses the current observation
relative to a recent regime whose center and dispersion already reflect the
recent mixture of ordinary states and stress events.

## Current reading

Using the 2026-07-27 VIX Close of 18.67:

- relative Log deviation: 0.0200;
- VIX Z-score: 0.125;
- bounded normal-score: 54.96%.

This is a relative VIX-location score. It is not a crash probability or an
empirical percentile. In the composite indicator, the VIX bubble/complacency
component reverses the direction to `1 - normal score`, because lower relative
VIX represents higher complacency risk. The corresponding current complacency
score is 45.04%.

## Decision

The VIX analysis retains three linked layers:

1. Raw versus Log daily Close establishes that logging materially improves the
   distributional shape.
2. The existing High-based event classifier shows that much of the right tail
   is event-driven and that event frequency increased after 2008, while the
   ordinary-state center remained broadly stable.
3. The same two-stage 120-month rolling calculation used for SKEW evaluates the
   current monthly Close against a regime that includes both ordinary and event
   observations.

The canonical calculations are in `src/market_risk/vix.py`. The VIX validation
notebook and the integrated composite notebook use the shared transformation.
