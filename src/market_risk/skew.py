"""Canonical two-stage rolling transformation for the SKEW risk component."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm


def compute_skew_risk_frame(
    monthly: pd.DataFrame,
    value_col: str = "SKEW_Close",
    window: int = 120,
) -> pd.DataFrame:
    """Return the current-inclusive two-stage rolling SKEW transformation.

    The normal CDF output is a bounded risk score. It is not claimed to be a
    historically calibrated percentile.
    """
    if value_col not in monthly.columns:
        raise KeyError(f"Missing required column: {value_col}")
    if window < 2:
        raise ValueError("window must be at least 2")

    values = pd.to_numeric(monthly[value_col], errors="coerce")
    observed = values.dropna()
    if observed.empty:
        raise ValueError("SKEW series has no numeric observations")
    if (observed <= 0).any():
        raise ValueError("SKEW values must be positive before log transformation")

    result = monthly.copy()
    result["Log_SKEW"] = np.log(values)
    result["Log_10Y_Avg"] = result["Log_SKEW"].rolling(window).mean()
    result["Log_Deviation"] = (
        result["Log_SKEW"] - result["Log_10Y_Avg"]
    ) / result["Log_10Y_Avg"]
    result["Dev_10Y_Avg"] = result["Log_Deviation"].rolling(window).mean()
    result["Dev_10Y_Std"] = result["Log_Deviation"].rolling(window).std()
    result["Z_Score"] = (
        result["Log_Deviation"] - result["Dev_10Y_Avg"]
    ) / result["Dev_10Y_Std"]
    result["Normal_Risk_Score"] = norm.cdf(result["Z_Score"])
    return result
