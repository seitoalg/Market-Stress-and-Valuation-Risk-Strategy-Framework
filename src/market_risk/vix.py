"""Canonical VIX transformations and stress-event classification."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm


def compute_vix_risk_frame(
    monthly: pd.DataFrame,
    value_col: str = "VIX_Close",
    window: int = 120,
) -> pd.DataFrame:
    """Return the current-inclusive two-stage rolling VIX transformation.

    The calculation intentionally matches the SKEW component. The normal CDF
    output is a bounded relative score, not a calibrated probability or an
    empirical percentile.
    """
    if value_col not in monthly.columns:
        raise KeyError(f"Missing required column: {value_col}")
    if window < 2:
        raise ValueError("window must be at least 2")

    values = pd.to_numeric(monthly[value_col], errors="coerce")
    observed = values.dropna()
    if observed.empty:
        raise ValueError("VIX series has no numeric observations")
    if (observed <= 0).any():
        raise ValueError("VIX values must be positive before log transformation")

    result = monthly.copy()
    result["Log_VIX"] = np.log(values)
    result["Log_10Y_Avg"] = result["Log_VIX"].rolling(window).mean()
    result["Log_Deviation"] = (
        result["Log_VIX"] - result["Log_10Y_Avg"]
    ) / result["Log_10Y_Avg"]
    result["Dev_10Y_Avg"] = result["Log_Deviation"].rolling(window).mean()
    result["Dev_10Y_Std"] = result["Log_Deviation"].rolling(window).std()
    result["Z_Score"] = (
        result["Log_Deviation"] - result["Dev_10Y_Avg"]
    ) / result["Dev_10Y_Std"]
    result["Normal_Risk_Score"] = norm.cdf(result["Z_Score"])
    return result


def classify_vix_stress_events(
    daily: pd.DataFrame,
    high_col: str = "VIX_High",
    window_months: int = 360,
    exit_consecutive_days: int = 10,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Classify the VIX stress states used by the existing event strategy.

    A stress event starts when the completed daily High exceeds the point-in-
    time +2 sigma threshold. It ends after ``exit_consecutive_days`` completed
    daily High observations below +1 sigma.

    Before the first complete long-run window, the function preserves the
    strategy's intentional retrospective use of the first available baseline.
    Once the full window exists, each daily threshold uses completed prior
    monthly highs plus the current month-to-date high.
    """
    if high_col not in daily.columns:
        raise KeyError(f"Missing required column: {high_col}")
    if window_months < 2:
        raise ValueError("window_months must be at least 2")
    if exit_consecutive_days < 1:
        raise ValueError("exit_consecutive_days must be positive")
    if not isinstance(daily.index, pd.DatetimeIndex):
        raise TypeError("daily must use a DatetimeIndex")

    values = pd.to_numeric(daily[high_col], errors="coerce")
    observed = values.dropna()
    if observed.empty:
        raise ValueError("VIX High series has no numeric observations")
    if (observed <= 0).any():
        raise ValueError("VIX High values must be positive")

    result = daily.copy().sort_index()
    result[high_col] = pd.to_numeric(result[high_col], errors="coerce")
    result = result.dropna(subset=[high_col])

    monthly_high = result[high_col].resample("ME").max()
    rolling_mean = monthly_high.rolling(window_months).mean()
    rolling_std = monthly_high.rolling(window_months).std(ddof=0)
    first_valid = rolling_mean.first_valid_index()
    if first_valid is None:
        raise ValueError(
            f"At least {window_months} monthly observations are required"
        )

    first_mean = float(rolling_mean.loc[first_valid])
    first_std = float(rolling_std.loc[first_valid])

    result["Month_End"] = result.index.to_period("M").to_timestamp("M")
    result["Month_To_Date_High"] = result.groupby("Month_End")[high_col].cummax()
    result["Mean_Long_Run"] = np.nan
    result["Std_Long_Run"] = np.nan

    for month_end, rows in result.groupby("Month_End"):
        row_index = rows.index
        if month_end < first_valid:
            result.loc[row_index, "Mean_Long_Run"] = first_mean
            result.loc[row_index, "Std_Long_Run"] = first_std
            continue

        prior_months = monthly_high.loc[monthly_high.index < month_end].tail(
            window_months - 1
        )
        if len(prior_months) != window_months - 1:
            raise ValueError(
                f"Expected {window_months - 1} completed months before "
                f"{month_end.date()}, found {len(prior_months)}"
            )

        prior_sum = prior_months.sum()
        prior_sum_sq = np.square(prior_months.to_numpy()).sum()
        current_high = rows["Month_To_Date_High"].astype(float)
        point_in_time_mean = (prior_sum + current_high) / window_months
        point_in_time_variance = (
            (prior_sum_sq + np.square(current_high)) / window_months
            - np.square(point_in_time_mean)
        ).clip(lower=0)

        result.loc[row_index, "Mean_Long_Run"] = point_in_time_mean.to_numpy()
        result.loc[row_index, "Std_Long_Run"] = np.sqrt(
            point_in_time_variance.to_numpy()
        )

    result["+1_Sigma"] = result["Mean_Long_Run"] + result["Std_Long_Run"]
    result["+2_Sigma"] = result["Mean_Long_Run"] + 2 * result["Std_Long_Run"]
    result["Above_2_Sigma"] = result[high_col] > result["+2_Sigma"]
    result["Below_1_Sigma"] = result[high_col] < result["+1_Sigma"]
    result["In_Stress_Event"] = False
    result["Event_ID"] = pd.Series(pd.NA, index=result.index, dtype="Int64")

    event_records: list[dict[str, object]] = []
    in_event = False
    event_id = 0
    below_one_count = 0
    event_start: pd.Timestamp | None = None
    event_max = -np.inf
    event_max_date: pd.Timestamp | None = None

    for date, row in result.iterrows():
        if not in_event and bool(row["Above_2_Sigma"]):
            in_event = True
            event_id += 1
            below_one_count = 0
            event_start = date
            event_max = float(row[high_col])
            event_max_date = date

        if not in_event:
            continue

        result.at[date, "In_Stress_Event"] = True
        result.at[date, "Event_ID"] = event_id

        if float(row[high_col]) > event_max:
            event_max = float(row[high_col])
            event_max_date = date

        if bool(row["Below_1_Sigma"]):
            below_one_count += 1
        else:
            below_one_count = 0

        if below_one_count >= exit_consecutive_days:
            event_records.append(
                {
                    "Event_ID": event_id,
                    "Event_Start_Date": event_start,
                    "Event_End_Date": date,
                    "Max_VIX_Date": event_max_date,
                    "Max_VIX": event_max,
                }
            )
            in_event = False
            below_one_count = 0
            event_start = None
            event_max = -np.inf
            event_max_date = None

    if in_event:
        event_records.append(
            {
                "Event_ID": event_id,
                "Event_Start_Date": event_start,
                "Event_End_Date": result.index[-1],
                "Max_VIX_Date": event_max_date,
                "Max_VIX": event_max,
            }
        )

    events = pd.DataFrame(event_records)
    return result, events
