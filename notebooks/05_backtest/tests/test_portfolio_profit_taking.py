import unittest

import pandas as pd

from src.backtest.portfolio import ASSETS, PortfolioBacktester


class ProfitTakingSchedulingTests(unittest.TestCase):
    def test_crossing_multiple_tiers_schedules_each_tier(self) -> None:
        engine = PortfolioBacktester.__new__(PortfolioBacktester)
        engine.dates = pd.date_range("2026-01-02", periods=3, freq="B")
        engine.orders = {}
        engine.tier_fired = {asset: set() for asset in ASSETS}
        engine.previous_z = {asset: 0.5 for asset in ASSETS}

        row = pd.Series({"TQQQ_Z": 3.2, "GLD_Z": 0.5, "TLT_Z": 0.5})
        engine._schedule_profit_taking(engine.dates[0], row)

        orders = engine.orders[engine.dates[1]]
        self.assertEqual([order["Tier"] for order in orders], [1, 2, 3])
        self.assertEqual(
            [order["Fraction"] for order in orders], [0.25, 0.50, 1.00]
        )
        self.assertEqual(engine.tier_fired["TQQQ"], {1, 2, 3})


if __name__ == "__main__":
    unittest.main()
