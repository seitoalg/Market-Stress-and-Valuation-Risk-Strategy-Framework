# Dynamic Cash, Valuation, and VIX Event Backtest Specification

## Status

This document freezes the first implementable version of the portfolio
backtest agreed on 2026-08-06. Parameters may later be tested in sensitivity
analysis, but must not be changed inside the baseline run.

## Objective

The strategy seeks long-run portfolio weights of 60% TQQQ, 30% GLD, and 10%
TLT without treating cash as a fourth strategic allocation. Cash is a dynamic
state created by gradual purchases, dividends, and profit-taking. Normal
monthly purchases converge toward the target without forcing immediate full
investment. VIX stress events create an asymmetric exception that may push
TQQQ above its 60% target.

## Initial state and target

- Initial capital: USD 10,000.
- Initial positions: none.
- Initial cash: USD 10,000.
- External deposits and withdrawals: none.
- Target portfolio weights, measured against total marked-to-market equity:
  - TQQQ: 60%.
  - GLD: 30%.
  - TLT: 10%.
- Cash has no fixed target weight.
- Fractional ETF shares are allowed.

## Data timing and execution

- A signal is evaluated only after its input bar is complete.
- Every order is executed at the next available trading day's opening price.
- Buy execution price: next open multiplied by 1.0005.
- Sell execution price: next open multiplied by 0.9995.
- Commissions: zero.
- Taxes: excluded.
- Distributions are not reinvested automatically. Cash distributions are
  credited to strategy cash.

## Historical TQQQ construction

- Before usable TQQQ history begins, calculate the daily adjusted QQQ total
  return and multiply that daily return by three.
- Compound those daily returns into a synthetic TQQQ return index.
- For pre-inception execution, construct the synthetic opening value from the
  prior synthetic close and three times QQQ's adjusted overnight return; build
  the synthetic closing value from three times QQQ's adjusted close-to-close
  return. Reject any day whose leveraged gross return is not positive.
- From the first usable actual TQQQ daily return onward, use actual TQQQ.
- Join the synthetic and actual segments by returns, not by raw price levels,
  so the splice has no artificial price jump.
- During the actual-ETF segment, mark positions using unadjusted prices and
  credit actual cash distributions separately.

## Rolling valuation transformations

All valuation signals use completed monthly observations and a trailing
120-month, current-inclusive, two-stage rolling transformation.

1. Apply the indicator's value transformation.
2. Calculate the relative deviation from its trailing 120-month mean.
3. Standardize that deviation against its own trailing 120-month mean and
   sample standard deviation.
4. Map the resulting Z-score through the standard-normal CDF when a bounded
   recommendation score is needed.

Value transformations:

- Shiller CAPE: raw positive value.
- DXY: natural log.
- U.S. 30-year Treasury yield: natural log of the yield expressed in percentage
  points, for example `4.5`, not decimal form `0.045`.
- VIX and SKEW risk-model inputs: natural log.
- Zero or negative observations are invalid for a log transformation.

## Asset valuation orientation and recommendation strength

Define an expensive-direction Z-score for each traded asset:

- TQQQ: `Z_expensive = Z_CAPE`.
- GLD: `Z_expensive = -Z_DXY`.
- TLT: `Z_expensive = -Z_30Y_Yield`.

The normal monthly buy recommendation is:

```text
recommendation = 2 * NormalCDF(-Z_expensive)
```

The score approaches two when the asset is statistically cheap, equals one at
zero sigma, and approaches zero when the asset is statistically expensive.
VIX is not numerically blended with CAPE. It is a separate event overlay.

## Normal monthly purchase rule

At each completed month end, calculate for asset `i`:

```text
current_weight_i = market_value_i / total_equity
weight_gap_i = max(0, target_weight_i - current_weight_i)
```

The VIX research sample contains 12 classified events over approximately 36.56
years, equivalent to one event per 36.6 months. Half that interval, 18.3
months, is the baseline convergence time constant.

```text
normal_buy_i = (
    total_equity
    * weight_gap_i
    / 18.3
    * recommendation_i
)
```

Equivalently, in the requested cash-coefficient form:

```text
coefficient_i = (
    total_equity
    * weight_gap_i
    / (18.3 * cash)
)
normal_buy_i = cash * coefficient_i * recommendation_i
```

The coefficient is recalculated every month. In the absence of price changes,
events, or sales, the remaining gap converges geometrically rather than being
closed on a fixed date. Normal orders must be proportionally scaled if their
sum would consume all available cash; the normal process must leave positive
cash after every finite number of monthly updates.

## VIX stress-event overlay

Retain the canonical event classification and wave-entry logic already used by
the repository:

- A stress event starts when the point-in-time VIX High reaches its rolling
  plus-two-sigma threshold.
- A wave ends after five trading days below plus two sigma and can be rearmed by
  a new breach.
- The full event ends after ten trading days below plus one sigma.
- A maximum of three event purchase signals may execute during one event.

At event start, freeze the available cash as `event_start_cash`.

```text
event_purchase_amount = event_start_cash / 3
```

- Each valid event signal buys that fixed dollar amount of TQQQ at the next
  trading day's opening execution price.
- The third purchase may exhaust the event-start cash budget.
- Event purchases may take TQQQ above its 60% target.
- Unused tranches remain cash when an event ends before three purchases.
- If a VIX event purchase occurs during a calendar month, or the event remains
  active at that month end, skip the next normal monthly purchases for TQQQ,
  GLD, and TLT.
- Profit-taking remains active during VIX events.

## Profit-taking rule

Profit-taking uses the same expensive-direction Z-score that controls the
asset's normal buy recommendation. For each asset, calculate:

```text
target_value_i = target_weight_i * total_equity
excess_value_i = max(0, market_value_i - target_value_i)
```

A sale requires all of the following:

- The asset is above its target value.
- At least one profitable acquisition lot is available.
- The expensive-direction Z-score crosses a configured tier from below.

Tier actions, each applied to the excess that exists at that tier's signal:

- Cross above +1 sigma: sell 25% of the current excess.
- Cross above +2 sigma: additionally sell 50% of the then-current excess.
- Cross above +3 sigma: sell 100% of the then-current excess, returning the
  asset to its target value.

Each tier can execute only once per armed cycle. Crossing directly to a higher
tier executes the highest applicable action. After the expensive-direction
Z-score returns to zero sigma or below, rearm all three tiers. Sell profitable
lots first and maintain lot-level cost basis and realized profit records. Sale
proceeds return to cash.

## Order priority

When multiple actions share an execution date, process them in this order:

1. Profit-taking sales.
2. Credit sale proceeds to cash.
3. VIX event purchases.
4. Normal monthly purchases, unless suspended for the event month.

## Required accounting and audit output

The engine must retain enough information to reproduce every decision:

- Daily cash, position market values, and total equity.
- Shares and lot-level cost basis by asset.
- Dividends, slippage, realized profit, and unrealized profit.
- Current weights, target gaps, Z-scores, CDF scores, and recommendation
  strengths at every monthly decision.
- VIX event ID, wave, frozen event-start cash, tranche number, signal date, and
  execution date.
- Profit-taking tier state, reset dates, signal dates, and execution dates.
- A transaction ledger with explicit reason codes.

## Baseline reports

Report at minimum:

- Ending equity and CAGR.
- Maximum drawdown and its dates.
- Annualized volatility and Sharpe ratio, with the selected cash-rate
  convention disclosed.
- Total and per-asset realized profit.
- Time-weighted average cash weight and minimum cash balance.
- Number of normal purchases, event purchases, and tiered profit-taking sales.
- Comparison against buy-and-hold QQQ, TQQQ, and the continuously rebalanced
  60/30/10 portfolio over the common sample.

Sensitivity runs should later compare zero versus 10 basis points of
slippage, fractional versus whole shares, event-month normal-purchase
suspension on versus off, and the full-sample 18.3-month time constant against
the post-2008 alternative of approximately 14 months.

