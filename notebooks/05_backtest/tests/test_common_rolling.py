import unittest

import numpy as np
import pandas as pd

from src.market_risk.rolling import (
    compute_point_in_time_daily_z,
    compute_two_stage_rolling_risk,
)
from src.market_risk.transforms import identity_transform, log_transform


class CommonRollingTests(unittest.TestCase):
    def test_identity_and_log_transforms(self) -> None:
        values = pd.Series([1.0, np.e, np.e**2])

        pd.testing.assert_series_equal(identity_transform(values), values)
        pd.testing.assert_series_equal(
            log_transform(values), pd.Series([0.0, 1.0, 2.0])
        )

    def test_log_transform_rejects_non_positive_values(self) -> None:
        with self.assertRaisesRegex(ValueError, "must be positive"):
            log_transform(pd.Series([1.0, 0.0]))

    def test_two_stage_rolling_matches_direct_formula(self) -> None:
        values = pd.Series(np.linspace(10.0, 30.0, 30))
        window = 5
        actual = compute_two_stage_rolling_risk(values, window=window)
        mean = values.rolling(window).mean()
        deviation = (values - mean) / mean
        deviation_mean = deviation.rolling(window).mean()
        deviation_std = deviation.rolling(window).std()

        pd.testing.assert_series_equal(
            actual["Z_Score"],
            (deviation - deviation_mean) / deviation_std,
            check_names=False,
        )

    def test_daily_point_in_time_uses_prior_months_plus_today(self) -> None:
        monthly = pd.Series(
            np.linspace(10.0, 30.0, 30),
            index=pd.period_range("2000-01", periods=30, freq="M"),
        )
        today = pd.Timestamp("2002-07-15")
        daily = pd.Series([32.0], index=[today])
        window = 5

        actual = compute_point_in_time_daily_z(daily, monthly, window=window)
        monthly_mean = monthly.rolling(window).mean()
        monthly_deviation = (monthly - monthly_mean) / monthly_mean
        stage_one = np.append(monthly.iloc[-4:].to_numpy(), 32.0)
        current_deviation = (32.0 - stage_one.mean()) / stage_one.mean()
        stage_two = np.append(
            monthly_deviation.dropna().iloc[-4:].to_numpy(), current_deviation
        )
        expected = (current_deviation - stage_two.mean()) / stage_two.std(ddof=1)

        self.assertAlmostEqual(float(actual.loc[today]), float(expected))


if __name__ == "__main__":
    unittest.main()
