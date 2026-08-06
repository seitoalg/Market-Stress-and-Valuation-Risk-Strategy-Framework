"""Reusable value transformations for market-risk indicators."""

from __future__ import annotations

import numpy as np
import pandas as pd


def identity_transform(values: pd.Series) -> pd.Series:
    """Return numeric values without changing their scale."""
    return pd.to_numeric(values, errors="coerce")


def log_transform(values: pd.Series) -> pd.Series:
    """Return the natural log of a strictly positive numeric series."""
    numeric = pd.to_numeric(values, errors="coerce")
    observed = numeric.dropna()
    if (observed <= 0).any():
        raise ValueError("log-transform observations must be positive")
    return np.log(numeric)
