import unittest

import numpy as np
import pandas as pd

from src.market_risk.skew import compute_skew_risk_frame


class SkewTransformTests(unittest.TestCase):
    def setUp(self):
        index = pd.date_range("2000-01-31", periods=300, freq="ME")
        values = 110.0 * np.exp(np.linspace(0.0, 0.25, len(index)))
        self.monthly = pd.DataFrame({"SKEW_Close": values}, index=index)

    def test_matches_the_documented_two_stage_formula(self):
        window = 120
        result = compute_skew_risk_frame(self.monthly, window=window)
        log_value = np.log(self.monthly["SKEW_Close"])
        log_average = log_value.rolling(window).mean()
        deviation = (log_value - log_average) / log_average
        deviation_average = deviation.rolling(window).mean()
        deviation_std = deviation.rolling(window).std()
        expected_z = (deviation - deviation_average) / deviation_std

        pd.testing.assert_series_equal(
            result["Z_Score"],
            expected_z,
            check_names=False,
        )

    def test_first_valid_z_uses_current_in_both_windows(self):
        result = compute_skew_risk_frame(self.monthly, window=120)
        self.assertEqual(result["Z_Score"].first_valid_index(), self.monthly.index[238])

    def test_does_not_mutate_input(self):
        original = self.monthly.copy(deep=True)
        compute_skew_risk_frame(self.monthly)
        pd.testing.assert_frame_equal(self.monthly, original)

    def test_rejects_non_positive_values(self):
        invalid = self.monthly.copy()
        invalid.iloc[-1, 0] = 0
        with self.assertRaisesRegex(ValueError, "must be positive"):
            compute_skew_risk_frame(invalid)


if __name__ == "__main__":
    unittest.main()
