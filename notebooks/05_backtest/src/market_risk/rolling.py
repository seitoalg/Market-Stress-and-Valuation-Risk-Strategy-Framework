"""Reusable rolling calculations for market-risk indicators."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm


def compute_two_stage_rolling_risk(
    values: pd.Series,
    *,
    window: int = 120,
) -> pd.DataFrame:
    """Compute the current-inclusive two-stage rolling relative Z-score."""
    if window < 2:
        raise ValueError("window must be at least 2 observations")

    numeric = pd.to_numeric(values, errors="coerce")
    rolling_mean = numeric.rolling(window=window, min_periods=window).mean()
    deviation = (numeric - rolling_mean) / rolling_mean
    deviation_mean = deviation.rolling(
        window=window, min_periods=window
    ).mean()
    deviation_std = deviation.rolling(
        window=window, min_periods=window
    ).std(ddof=1)
    z_score = (deviation - deviation_mean) / deviation_std

    return pd.DataFrame(
        {
            "Rolling_Mean": rolling_mean,
            "Deviation": deviation,
            "Deviation_Mean": deviation_mean,
            "Deviation_Std": deviation_std,
            "Z_Score": z_score,
            "Normal_Risk_Score": norm.cdf(z_score),
        },
        index=values.index,
    )


def compute_point_in_time_daily_z(
    daily_values: pd.Series,
    monthly_values: pd.Series,
    *,
    window: int = 120,
) -> pd.Series:
    """Use prior completed months plus today's value for a daily Z-score."""
    if window < 2:
        raise ValueError("window must be at least 2 observations")

    daily = pd.to_numeric(daily_values, errors="coerce").dropna().sort_index()
    monthly = pd.to_numeric(monthly_values, errors="coerce").dropna().sort_index()
    if not isinstance(monthly.index, pd.PeriodIndex):
        monthly.index = pd.DatetimeIndex(monthly.index).to_period("M")

    monthly_deviations = compute_two_stage_rolling_risk(
        monthly, window=window
    )["Deviation"].dropna()
    output: dict[pd.Timestamp, float] = {}
    for date, current in daily.items():
        period = pd.Timestamp(date).to_period("M")
        prior_values = monthly.loc[monthly.index < period].tail(window - 1)
        prior_deviations = monthly_deviations.loc[
            monthly_deviations.index < period
        ].tail(window - 1)
        if len(prior_values) != window - 1 or len(prior_deviations) != window - 1:
            continue

        stage_one = np.append(prior_values.to_numpy(dtype=float), float(current))
        current_mean = float(stage_one.mean())
        current_deviation = (float(current) - current_mean) / current_mean
        stage_two = np.append(
            prior_deviations.to_numpy(dtype=float), current_deviation
        )
        output[pd.Timestamp(date)] = (
            current_deviation - float(stage_two.mean())
        ) / float(stage_two.std(ddof=1))

    return pd.Series(output, name="Z_Score", dtype=float)
