"""Distribution diagnostics for Cboe SKEW.

Scope:
- describe raw and log SKEW distributions;
- compare daily and completed-month closing observations;
- check stability across broad market regimes;
- inspect the exact two-stage rolling Z transformation used by the
  composite market-risk indicator.

This is parameter validation, not an event study or trading backtest.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
import yfinance as yf
import yfinance.cache as yf_cache
from scipy import stats
from src.market_risk.skew import compute_skew_risk_frame

matplotlib.use("Agg")
import matplotlib.pyplot as plt


START_DATE = "1990-01-01"
ROLLING_MONTHS = 120
OUTPUT_DIR = Path("reports/generated/skew_distribution")


def distribution_stats(series: pd.Series, name: str) -> pd.Series:
    """Return descriptive diagnostics without treating observations as IID."""
    clean = series.dropna().astype(float)
    shapiro_sample = (
        clean.sample(5000, random_state=42) if len(clean) > 5000 else clean
    )
    shapiro_stat, shapiro_p = stats.shapiro(shapiro_sample)
    jb = stats.jarque_bera(clean)

    return pd.Series(
        {
            "Name": name,
            "Count": len(clean),
            "Mean": clean.mean(),
            "Std": clean.std(),
            "Median": clean.median(),
            "Min": clean.min(),
            "Max": clean.max(),
            "Skewness": stats.skew(clean),
            "Kurtosis_Excess": stats.kurtosis(clean),
            "Lag1_Autocorrelation": clean.autocorr(lag=1),
            "Shapiro_Stat": shapiro_stat,
            "Shapiro_p": shapiro_p,
            "Jarque_Bera": jb.statistic,
            "Jarque_Bera_p": jb.pvalue,
        }
    )


def download_skew(run_date: pd.Timestamp) -> tuple[pd.Series, pd.Timestamp]:
    """Download daily SKEW Close using a writable temporary cache."""
    yf_cache.set_cache_location(tempfile.mkdtemp(prefix="skew-yfinance-"))
    end_exclusive = (run_date.normalize() + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    raw = yf.download(
        "^SKEW",
        start=START_DATE,
        end=end_exclusive,
        auto_adjust=False,
        progress=False,
    )
    if raw.empty:
        raise RuntimeError("Yahoo Finance returned no ^SKEW observations.")
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    close = raw["Close"].dropna().astype(float).rename("SKEW_Close")
    return close, close.index[-1]


def build_monthly_samples(
    daily_close: pd.Series, run_date: pd.Timestamp
) -> tuple[pd.Series, pd.Series, pd.Timestamp]:
    """Separate completed-month history from the provisional current month."""
    monthly_all = daily_close.resample("ME").last().dropna()
    current_month_end = run_date.normalize() + pd.offsets.MonthEnd(0)
    completed = monthly_all.loc[monthly_all.index < current_month_end].copy()

    model_monthly = completed.copy()
    model_monthly.loc[current_month_end] = daily_close.iloc[-1]
    model_monthly = model_monthly.sort_index()
    return completed, model_monthly, current_month_end


def build_model_transform(monthly_close: pd.Series) -> pd.DataFrame:
    """Reproduce the SKEW transformation used in the composite indicator."""
    model = compute_skew_risk_frame(
        monthly_close.to_frame("SKEW_Close"),
        window=ROLLING_MONTHS,
    )
    model["Risk_Percentile"] = model["Normal_Risk_Score"] * 100

    # Sensitivity benchmarks only; these do not replace the live model.
    log_std_120 = model["Log_SKEW"].rolling(ROLLING_MONTHS).std()
    model["Simple_Log_Z_120"] = (
        model["Log_SKEW"] - model["Log_10Y_Avg"]
    ) / log_std_120
    model["Simple_Normal_Risk"] = (
        stats.norm.cdf(model["Simple_Log_Z_120"]) * 100
    )
    model["Empirical_Percentile_120"] = (
        model["Log_SKEW"]
        .rolling(ROLLING_MONTHS)
        .apply(lambda x: np.mean(x <= x[-1]) * 100, raw=True)
    )
    return model


def save_distribution_figures(
    series_to_plot: list[tuple[pd.Series, str]],
    regime_data: dict[str, pd.Series],
    model: pd.DataFrame,
) -> None:
    """Save the core distribution and model-transformation diagnostics."""
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    for axis, (series, title) in zip(axes.flat, series_to_plot):
        clean = series.dropna()
        axis.hist(clean, bins=50, density=True, alpha=0.65)
        x = np.linspace(clean.min(), clean.max(), 300)
        axis.plot(x, stats.norm.pdf(x, clean.mean(), clean.std()), linewidth=2)
        axis.set_title(title)
        axis.set_ylabel("Density")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "raw_log_histograms.png", dpi=160)
    plt.close(fig)

    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    for axis, (series, title) in zip(axes.flat, series_to_plot):
        stats.probplot(series.dropna(), dist="norm", plot=axis)
        axis.set_title(f"Q-Q plot: {title}")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "raw_log_qq_plots.png", dpi=160)
    plt.close(fig)

    fig, axes = plt.subplots(1, len(regime_data), figsize=(16, 5))
    for axis, (name, series) in zip(np.atleast_1d(axes), regime_data.items()):
        stats.probplot(series.dropna(), dist="norm", plot=axis)
        axis.set_title(f"{name}: log monthly Close")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "regime_qq_plots.png", dpi=160)
    plt.close(fig)

    valid_model = model.dropna(subset=["Z_Score"])
    fig, axes = plt.subplots(2, 1, figsize=(14, 9))
    axes[0].plot(model.index, model["Z_Score"], linewidth=1)
    axes[0].axhline(0, color="black", linewidth=1)
    axes[0].axhline(2, linestyle="--", linewidth=1)
    axes[0].axhline(-2, linestyle="--", linewidth=1)
    axes[0].set_title("Composite-model SKEW Z-score through time")
    axes[0].grid(alpha=0.25)

    z = valid_model["Z_Score"]
    axes[1].hist(z, bins=30, density=True, alpha=0.65)
    x = np.linspace(z.min(), z.max(), 300)
    axes[1].plot(x, stats.norm.pdf(x), linewidth=2, label="Standard normal")
    axes[1].set_title("Distribution of composite-model SKEW Z-score")
    axes[1].legend()
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "composite_model_z_diagnostics.png", dpi=160)
    plt.close(fig)


def main() -> None:
    run_timestamp = pd.Timestamp.now(tz="UTC")
    run_date = run_timestamp.tz_localize(None)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    daily_close, latest_date = download_skew(run_date)
    completed_monthly, model_monthly, current_month_end = build_monthly_samples(
        daily_close, run_date
    )

    daily_log = np.log(daily_close).rename("Log_SKEW_Close")
    monthly_log = np.log(completed_monthly).rename("Log_Monthly_SKEW_Close")

    series_to_plot = [
        (daily_close, "Raw daily SKEW Close"),
        (daily_log, "Log daily SKEW Close"),
        (completed_monthly, "Raw completed-month SKEW Close"),
        (monthly_log, "Log completed-month SKEW Close"),
    ]
    distribution_summary = pd.DataFrame(
        [distribution_stats(series, name) for series, name in series_to_plot]
    )

    regimes = {
        "1990-2007": ("1990-01-01", "2007-12-31"),
        "2008-2019": ("2008-01-01", "2019-12-31"),
        "2020-present": ("2020-01-01", None),
    }
    regime_data = {
        name: monthly_log.loc[start:end].dropna()
        for name, (start, end) in regimes.items()
    }
    regime_summary = pd.DataFrame(
        [distribution_stats(series, name) for name, series in regime_data.items()]
    )

    model = build_model_transform(model_monthly)
    valid_z = model["Z_Score"].dropna()
    model_z_summary = distribution_stats(valid_z, "Composite-model SKEW Z")
    normal_ks = stats.kstest(valid_z, "norm")
    risk_uniform_ks = stats.kstest(
        model.loc[valid_z.index, "Risk_Percentile"] / 100,
        "uniform",
    )

    distribution_summary.to_csv(
        OUTPUT_DIR / "distribution_summary.csv", index=False
    )
    regime_summary.to_csv(OUTPUT_DIR / "regime_summary.csv", index=False)
    model.to_csv(OUTPUT_DIR / "composite_model_transform.csv")
    pd.DataFrame(
        [
            {
                "Normal_KS_Statistic": normal_ks.statistic,
                "Normal_KS_p": normal_ks.pvalue,
                "Risk_Uniform_KS_Statistic": risk_uniform_ks.statistic,
                "Risk_Uniform_KS_p": risk_uniform_ks.pvalue,
            }
        ]
    ).to_csv(OUTPUT_DIR / "model_calibration_tests.csv", index=False)

    save_distribution_figures(series_to_plot, regime_data, model)

    latest_model = model.dropna(subset=["Z_Score"]).iloc[-1]
    print(f"Run timestamp (UTC): {run_timestamp.isoformat()}")
    print(f"Daily sample: {daily_close.index.min().date()} to {latest_date.date()}")
    print(
        "Completed-month sample:"
        f" {completed_monthly.index.min().date()}"
        f" to {completed_monthly.index.max().date()}"
    )
    print(
        f"Provisional model month: {current_month_end.date()}"
        f" using {latest_date.date()} close"
    )
    print("\n===== Distribution summary =====")
    print(distribution_summary.to_string(index=False))
    print("\n===== Regime summary: log completed-month Close =====")
    print(regime_summary.to_string(index=False))
    print("\n===== Composite-model transform =====")
    print(model_z_summary.to_string())
    print(f"Z vs N(0,1) KS p-value: {normal_ks.pvalue:.8g}")
    print(f"Risk percentile vs Uniform(0,1) KS p-value: {risk_uniform_ks.pvalue:.8g}")
    print(
        "Latest:"
        f" SKEW={latest_model['SKEW_Close']:.4f},"
        f" Z={latest_model['Z_Score']:.4f},"
        f" risk={latest_model['Risk_Percentile']:.2f}%"
    )
    print(
        "Latest sensitivity benchmarks:"
        f" simple-log-Z risk={latest_model['Simple_Normal_Risk']:.2f}%,"
        f" empirical 120M percentile="
        f"{latest_model['Empirical_Percentile_120']:.2f}%"
    )
    print(f"\nSaved outputs under: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
