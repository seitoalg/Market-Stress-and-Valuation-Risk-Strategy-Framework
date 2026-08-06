"""Shiller CAPE valuation-risk transformation."""

from __future__ import annotations

import pandas as pd

from .rolling import compute_two_stage_rolling_risk
from .transforms import identity_transform


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
    result = data.copy()
    cape = identity_transform(result[value_col])
    finite = cape.dropna()
    if finite.empty:
        raise ValueError("CAPE contains no numeric observations")
    if (finite <= 0).any():
        raise ValueError("CAPE observations must be positive")

    rolling = compute_two_stage_rolling_risk(cape, window=window)
    result["CAPE_10Y_Avg"] = rolling["Rolling_Mean"]
    result["CAPE_Deviation"] = rolling["Deviation"]
    result["Dev_10Y_Avg"] = rolling["Deviation_Mean"]
    result["Dev_10Y_Std"] = rolling["Deviation_Std"]
    result["Z_Score"] = rolling["Z_Score"]
    result["Normal_Risk_Score"] = rolling["Normal_Risk_Score"]
    return result
