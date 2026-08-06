import unittest

import numpy as np
import pandas as pd

from src.market_risk.cape import compute_cape_risk_frame


class CapeTransformTest(unittest.TestCase):
    def setUp(self) -> None:
        index = pd.date_range("2000-01-31", periods=360, freq="ME")
        trend = np.exp(np.linspace(np.log(10.0), np.log(35.0), len(index)))
        cycle = 1.0 + 0.22 * np.sin(np.linspace(0.0, 12.0 * np.pi, len(index)))
        self.data = pd.DataFrame({"CAPE": trend * cycle}, index=index)

    def test_matches_two_stage_formula(self) -> None:
        window = 120
        actual = compute_cape_risk_frame(self.data, window=window)

        cape_mean = self.data["CAPE"].rolling(window).mean()
        deviation = (self.data["CAPE"] - cape_mean) / cape_mean
        deviation_mean = deviation.rolling(window).mean()
        deviation_std = deviation.rolling(window).std()
        expected_z = (deviation - deviation_mean) / deviation_std

        pd.testing.assert_series_equal(
            actual["CAPE_Deviation"], deviation, check_names=False
        )
        pd.testing.assert_series_equal(actual["Z_Score"], expected_z, check_names=False)

    def test_uses_raw_cape_not_log_cape(self) -> None:
        actual = compute_cape_risk_frame(self.data)
        raw_mean = self.data["CAPE"].rolling(120).mean()
        expected = (self.data["CAPE"] - raw_mean) / raw_mean

        self.assertTrue(
            np.allclose(
                actual["CAPE_Deviation"].dropna(),
                expected.dropna(),
                rtol=0.0,
                atol=1e-12,
            )
        )

    def test_first_valid_z_requires_both_windows(self) -> None:
        actual = compute_cape_risk_frame(self.data, window=120)
        self.assertEqual(actual["Z_Score"].first_valid_index(), self.data.index[238])

    def test_does_not_mutate_input(self) -> None:
        before = self.data.copy(deep=True)
        compute_cape_risk_frame(self.data)
        pd.testing.assert_frame_equal(self.data, before)

    def test_rejects_non_positive_observation(self) -> None:
        data = self.data.copy()
        data.iloc[5, 0] = 0.0
        with self.assertRaises(ValueError):
            compute_cape_risk_frame(data)

    def test_rejects_missing_column(self) -> None:
        with self.assertRaises(KeyError):
            compute_cape_risk_frame(pd.DataFrame({"value": [1.0, 2.0]}))


if __name__ == "__main__":
    unittest.main()
