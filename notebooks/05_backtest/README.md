# Backtest

Work-in-progress implementation of the dynamic-cash TQQQ/GLD/TLT strategy.

## Baseline

- Initial capital: USD 10,000
- Target weights: TQQQ 60%, GLD 30%, TLT 10%
- Monthly gradual purchases with dynamic cash retention
- VIX event purchases in three frozen-cash tranches
- Daily profit-taking decisions at +1σ, +2σ, and +3σ
- Orders execute at the next trading day's open
- Daily CAPE uses the prior completed month's Shiller E10 denominator

## Run

```powershell
python scripts/run_portfolio_backtest.py
python -m unittest discover -s tests
```

Generated market data and result files are intentionally not committed in this progress snapshot.
