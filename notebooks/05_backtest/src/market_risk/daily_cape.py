"""Look-ahead-safe daily CAPE construction from monthly Shiller data."""

from __future__ import annotations

import numpy as np
import pandas as pd


def build_daily_cape(
    monthly_shiller: pd.DataFrame,
    spx_daily: pd.Series,
) -> pd.DataFrame:
    """Apply the prior month's Shiller Price/CAPE denominator to daily SPX."""
    required = {"Price", "CAPE"}
    if not required.issubset(monthly_shiller.columns):
        raise KeyError(f"monthly Shiller data missing: {sorted(required-set(monthly_shiller.columns))}")

    monthly = monthly_shiller[["Price", "CAPE"]].copy()
    if not isinstance(monthly.index, pd.PeriodIndex):
        monthly.index = pd.DatetimeIndex(monthly.index).to_period("M")
    monthly = monthly.sort_index()
    monthly["E10"] = monthly["Price"] / monthly["CAPE"]
    invalid = (
        ~np.isfinite(monthly["E10"])
        | monthly["Price"].le(0)
        | monthly["CAPE"].le(0)
        | monthly["E10"].le(0)
    )
    monthly.loc[invalid, "E10"] = np.nan

    spx = pd.to_numeric(spx_daily, errors="coerce").dropna().sort_index()
    source_periods = spx.index.to_period("M") - 1
    source = monthly.reindex(source_periods)
    source.index = spx.index

    result = pd.DataFrame(index=spx.index)
    result.index.name = "Date"
    result["SPX"] = spx
    result["E10_used"] = source["E10"]
    result["CAPE_daily"] = result["SPX"] / result["E10_used"]
    result["E10_source_month"] = source_periods.astype(str)
    result["Shiller_CAPE_source"] = source["CAPE"]
    result["Shiller_Price_source"] = source["Price"]
    result.loc[result["E10_used"].isna(), "E10_source_month"] = pd.NA
    return result
