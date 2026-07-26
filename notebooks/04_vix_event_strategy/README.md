# VIX Event Strategy

This research track defines stress events and tests staged purchases during those events. It is separate from the descriptive VIX distribution analysis.

## Event threshold

The event model uses the monthly VIX High on the raw VIX scale:

- Reference window: 360 monthly observations.
- After a full window exists: 359 completed monthly highs plus the current month-to-date High.
- Before a full window exists: the first completed 360-month mean and standard deviation are applied retrospectively.
- Event threshold: the rolling mean plus two standard deviations.

The early-period backfill is an intentional retrospective classification rule. It evaluates historical crises using the long-run baseline available to the completed research, rather than reproducing the information set of an investor living through the early sample.

## Point-in-time operation

Within the current month, the monthly High is updated cumulatively after each daily bar. Completed months remain fixed. A signal is evaluated after the daily bar and an entry is placed on the next available trading day.

The point-in-time reconstruction and its controlled comparison are documented in [Point-in-Time Monthly VIX High Validation](../../docs/validation/point-in-time-monthly-high.md).

## Event state rules

- An event begins when VIX reaches the rolling +2 sigma threshold.
- A wave ends after VIX remains below +2 sigma for five trading days.
- A new +2 sigma breach can rearm the next wave.
- The full event ends after VIX remains below +1 sigma for ten trading days.
- WMA-based entry timing and the maximum number of staged entries are evaluated within this event state.

The notebook currently focuses on event detection and entry timing. Full cash management, profit-taking, portfolio accounting, transaction assumptions, and benchmark comparisons will be added as the backtest layer is completed.
