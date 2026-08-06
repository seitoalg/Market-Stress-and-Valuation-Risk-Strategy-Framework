import unittest

import pandas as pd

from src.market_risk.daily_cape import build_daily_cape


class DailyCapeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.monthly = pd.DataFrame(
            {"Price": [100.0, 110.0], "CAPE": [20.0, 22.0]},
            index=pd.period_range("2025-12", periods=2, freq="M"),
        )
        self.spx = pd.Series(
            [120.0, 126.0, 132.0],
            index=pd.to_datetime(["2026-01-02", "2026-01-05", "2026-02-02"]),
        )

    def test_uses_only_prior_month_denominator(self) -> None:
        actual = build_daily_cape(self.monthly, self.spx)

        self.assertEqual(actual.loc["2026-01-02", "E10_source_month"], "2025-12")
        self.assertEqual(actual.loc["2026-02-02", "E10_source_month"], "2026-01")
        self.assertAlmostEqual(actual.loc["2026-01-02", "CAPE_daily"], 24.0)
        self.assertAlmostEqual(actual.loc["2026-02-02", "CAPE_daily"], 26.4)

    def test_same_month_cape_return_matches_spx_return(self) -> None:
        actual = build_daily_cape(self.monthly, self.spx)
        cape_return = (
            actual.loc["2026-01-05", "CAPE_daily"]
            / actual.loc["2026-01-02", "CAPE_daily"]
        )
        spx_return = self.spx.loc["2026-01-05"] / self.spx.loc["2026-01-02"]
        self.assertAlmostEqual(cape_return, spx_return)

    def test_missing_prior_month_is_not_forward_filled(self) -> None:
        spx = pd.Series([90.0], index=pd.to_datetime(["2025-12-01"]))
        actual = build_daily_cape(self.monthly, spx)
        self.assertTrue(pd.isna(actual.iloc[0]["CAPE_daily"]))


if __name__ == "__main__":
    unittest.main()
