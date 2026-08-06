# Backtest

> **重要:** この実装は検証途中です。現在の損益・CAGR・利益確定回数・特定日のCAPE/Z/CDFは確定値ではありません。先に [既知の問題・未確定事項](KNOWN_ISSUES.md) を確認してください。

Work-in-progress implementation of the dynamic-cash TQQQ/GLD/TLT strategy.

## Baseline

- Initial capital: USD 10,000
- Target weights: TQQQ 60%, GLD 30%, TLT 10%
- Monthly gradual purchases with dynamic cash retention
- VIX event purchases in three frozen-cash tranches
- Daily profit-taking decisions at +1σ, +2σ, and +3σ
- Orders execute at the next trading day's open
- Daily CAPE uses the prior completed month's Shiller E10 denominator

## Current validation status

The code has unit tests for structural behavior, but it has not yet passed value-level acceptance tests against the reference CAPE, rolling, buy-strength, and profit-taking calculations. Backtest outputs must be treated as provisional.

## Run

```powershell
python scripts/run_portfolio_backtest.py
python -m unittest discover -s tests
```

Generated market data and result files are intentionally not committed in this progress snapshot.
