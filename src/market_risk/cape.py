"""Shiller CAPE valuation-risk transformation."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm


def compute_cape_risk_frame(
    data: pd.DataFrame,
    *,
    value_col: str = "CAPE",
    window: int = 120,
) -> pd.DataFrame:
    """Return the two-stage, trend-adjusted CAPE valuation-risk series.

    The official transformation is:

    1. ``deviation = (CAPE - rolling_mean(CAPE)) / rolling_mean(CAPE)``
    2. Standardize that deviation against its own rolling mean and standard
       deviation.
    3. Map the resulting local Z-score through the standard-normal CDF.

    ``Normal_Risk_Score`` is the theoretical standard-normal cumulative
    probability corresponding to the local Z-score.
    """

    if value_col not in data.columns:
        raise KeyError(f"missing CAPE column: {value_col!r}")
    if window < 2:
        raise ValueError("window must be at least 2 observations")

    result = data.copy()
    cape = pd.to_numeric(result[value_col], errors="coerce")
    finite = cape.dropna()
    if finite.empty:
        raise ValueError("CAPE contains no numeric observations")
    if (finite <= 0).any():
        raise ValueError("CAPE observations must be positive")

    cape_mean = cape.rolling(window=window, min_periods=window).mean()
    deviation = (cape - cape_mean) / cape_mean
    deviation_mean = deviation.rolling(window=window, min_periods=window).mean()
    deviation_std = deviation.rolling(window=window, min_periods=window).std(ddof=1)
    z_score = (deviation - deviation_mean) / deviation_std

    result["CAPE_10Y_Avg"] = cape_mean
    result["CAPE_Deviation"] = deviation
    result["Dev_10Y_Avg"] = deviation_mean
    result["Dev_10Y_Std"] = deviation_std
    result["Z_Score"] = z_score
    result["Normal_Risk_Score"] = pd.Series(
        norm.cdf(z_score.to_numpy(dtype=float)),
        index=result.index,
        dtype=float,
    )
    return result
