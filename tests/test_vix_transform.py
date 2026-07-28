import unittest

import numpy as np
import pandas as pd

from src.market_risk.vix import (
    classify_vix_stress_events,
    compute_vix_risk_frame,
    prepare_vix_observations,
)


class VixTransformTests(unittest.TestCase):
    def setUp(self):
        index = pd.date_range("2000-01-31", periods=300, freq="ME")
        values = 18.0 * np.exp(np.linspace(0.0, 0.20, len(index)))
        self.monthly = pd.DataFrame({"VIX_Close": values}, index=index)

    def test_matches_the_documented_two_stage_formula(self):
        window = 120
        result = compute_vix_risk_frame(self.monthly, window=window)
        log_value = np.log(self.monthly["VIX_Close"])
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
        result = compute_vix_risk_frame(self.monthly, window=120)
        self.assertEqual(result["Z_Score"].first_valid_index(), self.monthly.index[238])

    def test_does_not_mutate_input(self):
        original = self.monthly.copy(deep=True)
        compute_vix_risk_frame(self.monthly)
        pd.testing.assert_frame_equal(self.monthly, original)

    def test_rejects_non_positive_values(self):
        invalid = self.monthly.copy()
        invalid.iloc[-1, 0] = 0
        with self.assertRaisesRegex(ValueError, "must be positive"):
            compute_vix_risk_frame(invalid)

    def test_event_classifier_uses_entry_and_consecutive_exit_rules(self):
        index = pd.to_datetime(
            [
                "2020-01-31",
                "2020-02-28",
                "2020-03-31",
                "2020-04-30",
                "2020-05-29",
                "2020-06-30",
                "2020-07-01",
                "2020-07-02",
                "2020-07-03",
            ]
        )
        daily = pd.DataFrame(
            {"VIX_High": [10.0] * 6 + [30.0, 10.0, 10.0]},
            index=index,
        )

        classified, events = classify_vix_stress_events(
            daily,
            window_months=6,
            exit_consecutive_days=2,
        )

        self.assertEqual(len(events), 1)
        self.assertEqual(events.iloc[0]["Event_Start_Date"], index[6])
        self.assertEqual(events.iloc[0]["Event_End_Date"], index[8])
        self.assertEqual(classified["In_Stress_Event"].sum(), 3)

    def test_invalid_high_does_not_remove_valid_close(self):
        index = pd.to_datetime(["2026-07-24", "2026-07-27"])
        raw = pd.DataFrame(
            {
                "High": [19.20, 0.0],
                "Close": [18.58, 18.67],
            },
            index=index,
        )

        close, high, diagnostics = prepare_vix_observations(raw)

        self.assertEqual(close.index[-1], index[-1])
        self.assertEqual(float(close.iloc[-1]), 18.67)
        self.assertNotIn(index[-1], high.index)
        self.assertEqual(diagnostics["High_Nonpositive"], 1)
        self.assertEqual(
            diagnostics["Valid_Close_Without_Valid_High"],
            1,
        )


if __name__ == "__main__":
    unittest.main()
