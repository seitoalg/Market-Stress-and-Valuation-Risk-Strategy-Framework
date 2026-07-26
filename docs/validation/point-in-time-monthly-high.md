# Point-in-Time Monthly VIX High Validation

Date: 2026-07-26

## Question

Does replacing the finalized monthly VIX High assigned to every day in a month with the High known on each historical date change the detected stress events or entry signals?

## Change

The event-strategy notebook now calculates:

1. a month-to-date VIX High for every daily observation;
2. the daily long-run reference from 359 completed monthly highs plus the current month-to-date High once 360 months are available;
3. the same backfilled long-run mean and standard deviation for the early period as the original model;
4. signals after the daily bar is complete, with entry on the next available trading day.

Only the current-month information treatment changed. WMA, wave, event-exit, and early backfill rules were held constant.

## Controlled comparison

Data source: Cboe VIX History via `datasets/finance-vix`

Period: 1990-01-02 to 2026-07-24

Cboe reports identical OHLC values before 2004-06-11 because only closing values were recorded for that period. Both threshold methods used the same input data, so this does not affect the controlled comparison.

| Result | Final-month method | Point-in-time method |
|---|---:|---:|
| Stress events | 12 | 12 |
| Buy signals | 16 | 16 |
| Changed daily +2 sigma classifications | — | 0 |
| Changed event start or end dates | — | 0 |
| Changed signal dates | — | 0 |
| Changed wave counts | — | 0 |

Additional threshold diagnostics:

- Mean absolute +2 sigma threshold difference: 0.002806.
- Maximum absolute +2 sigma threshold difference: 1.002005 on 2020-03-02.

## Conclusion

The point-in-time reconstruction improves chronological accuracy and alignment with live operation, but it does not change the historical events, entries, wave counts, or overall experimental conclusion in this sample.

The original finding was therefore not driven by assigning the finalized monthly High to earlier dates in the same month.
