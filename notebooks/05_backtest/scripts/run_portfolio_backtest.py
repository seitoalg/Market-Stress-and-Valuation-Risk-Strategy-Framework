"""Run the frozen dynamic-cash TQQQ/GLD/TLT portfolio backtest."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
import yfinance as yf
from scipy.stats import norm

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.backtest import BacktestConfig, PortfolioBacktester, detect_vix_wave_signals
from src.market_risk.cape import compute_cape_risk_frame
from src.market_risk.daily_cape import build_daily_cape
from src.market_risk.rolling import (
    compute_point_in_time_daily_z,
    compute_two_stage_rolling_risk,
)
from src.market_risk.transforms import log_transform


START = "1985-01-01"
END_EXCLUSIVE = "2026-08-01"
REPORT_DIR = REPO_ROOT / "reports" / "generated" / "portfolio_backtest"
SHILLER_API = (
    "https://posix4e.github.io/shiller_wrapper_data/data/stock_market_data.json"
)


def _flatten(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    if isinstance(result.columns, pd.MultiIndex):
        result.columns = result.columns.get_level_values(0)
    result.index = pd.DatetimeIndex(result.index).tz_localize(None)
    return result


def download_yahoo(symbol: str, start: str = START) -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = yf.download(
        symbol,
        start=start,
        end=END_EXCLUSIVE,
        auto_adjust=False,
        actions=True,
        progress=False,
        threads=False,
    )
    adjusted = yf.download(
        symbol,
        start=start,
        end=END_EXCLUSIVE,
        auto_adjust=True,
        actions=False,
        progress=False,
        threads=False,
    )
    if raw.empty or adjusted.empty:
        raise RuntimeError(f"Yahoo returned no data for {symbol}")
    return _flatten(raw), _flatten(adjusted)


def trade_frame(raw: pd.DataFrame) -> pd.DataFrame:
    result = raw[["Open", "Close"]].dropna().copy()
    dividend = raw.get("Dividends", pd.Series(0.0, index=raw.index))
    result["Dividend"] = pd.to_numeric(dividend, errors="coerce").fillna(0.0)
    return result


def build_spliced_tqqq(
    qqq_adjusted: pd.DataFrame,
    tqqq_raw: pd.DataFrame,
    tqqq_adjusted: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.Series]:
    qqq = qqq_adjusted[["Open", "Close"]].dropna()
    synthetic = pd.DataFrame(index=qqq.index, columns=["Open", "Close"], dtype=float)
    synthetic.iloc[0] = 100.0
    for position in range(1, len(qqq)):
        prior_qqq_close = float(qqq["Close"].iloc[position - 1])
        prior_synthetic_close = float(synthetic["Close"].iloc[position - 1])
        overnight = float(qqq["Open"].iloc[position]) / prior_qqq_close - 1
        close_return = float(qqq["Close"].iloc[position]) / prior_qqq_close - 1
        open_gross = 1 + 3 * overnight
        close_gross = 1 + 3 * close_return
        if open_gross <= 0 or close_gross <= 0:
            raise ValueError(f"non-positive synthetic TQQQ gross return on {qqq.index[position]}")
        synthetic.iloc[position, synthetic.columns.get_loc("Open")] = (
            prior_synthetic_close * open_gross
        )
        synthetic.iloc[position, synthetic.columns.get_loc("Close")] = (
            prior_synthetic_close * close_gross
        )
    synthetic["Dividend"] = 0.0

    actual = trade_frame(tqqq_raw)
    first_actual = actual.index.intersection(synthetic.index)[0]
    scale = float(synthetic.at[first_actual, "Close"] / actual.at[first_actual, "Close"])
    actual_scaled = actual * scale
    combined = pd.concat(
        [synthetic.loc[synthetic.index < first_actual], actual_scaled.loc[first_actual:]]
    ).sort_index()

    actual_adjusted = tqqq_adjusted["Close"].dropna()
    actual_total_scale = float(synthetic.at[first_actual, "Close"] / actual_adjusted.at[first_actual])
    total_return_close = pd.concat(
        [
            synthetic.loc[synthetic.index < first_actual, "Close"],
            actual_adjusted.loc[first_actual:] * actual_total_scale,
        ]
    ).sort_index()
    return combined, total_return_close


def get_cape_monthly() -> pd.Series:
    tables = pd.read_html("https://www.multpl.com/shiller-pe/table/by-month")
    cape = tables[0].copy()
    cape.columns = ["Date", "CAPE"]
    cape["Date"] = pd.to_datetime(cape["Date"], errors="coerce")
    cape["CAPE"] = pd.to_numeric(
        cape["CAPE"]
        .astype(str)
        .str.replace(",", "", regex=False)
        .str.extract(r"([0-9]+\.?[0-9]*)")[0],
        errors="coerce",
    )
    cape = cape.dropna().sort_values("Date")
    cape["Period"] = cape["Date"].dt.to_period("M")
    return cape.drop_duplicates("Period", keep="last").set_index("Period")["CAPE"]


def get_shiller_monthly(spx_close: pd.Series) -> pd.DataFrame:
    """Load Shiller Price/CAPE and extend completed recent months consistently."""
    response = requests.get(SHILLER_API, timeout=60)
    response.raise_for_status()
    raw = pd.DataFrame(response.json()["data"])
    raw["Period"] = pd.to_datetime(raw["date_string"]).dt.to_period("M")
    monthly = (
        raw.rename(columns={"sp500": "Price", "cape": "CAPE"})
        .dropna(subset=["Price", "CAPE"])
        .drop_duplicates("Period", keep="last")
        .set_index("Period")[["Price", "CAPE"]]
        .astype(float)
        .sort_index()
    )

    cape_extension = get_cape_monthly()
    periods = spx_close.dropna().index.to_period("M")
    spx_monthly_average = pd.Series(
        spx_close.to_numpy(dtype=float), index=periods
    ).groupby(level=0).mean()
    extension_periods = cape_extension.index[
        (cape_extension.index > monthly.index.max())
        & cape_extension.index.isin(spx_monthly_average.index)
    ]
    if len(extension_periods):
        extension = pd.DataFrame(
            {
                "Price": spx_monthly_average.loc[extension_periods],
                "CAPE": cape_extension.loc[extension_periods],
            }
        )
        monthly = pd.concat([monthly, extension]).sort_index()
    return monthly


def monthly_last(series: pd.Series) -> pd.Series:
    result = series.dropna().resample("ME").last()
    result.index = result.index.to_period("M")
    return result


def log_signal(series: pd.Series) -> pd.Series:
    values = pd.Series(series.to_numpy(dtype=float), index=series.index, name=series.name)
    transformed = log_transform(values)
    return compute_two_stage_rolling_risk(transformed, window=120)["Z_Score"]


def build_monthly_signals(
    cape: pd.Series,
    dxy_close: pd.Series,
    tyx_close: pd.Series,
    trading_dates: pd.DatetimeIndex,
) -> pd.DataFrame:
    cape_frame = pd.DataFrame({"CAPE": cape.to_numpy(dtype=float)}, index=cape.index.to_timestamp("M"))
    cape_z = compute_cape_risk_frame(cape_frame, window=120)["Z_Score"]
    cape_z.index = cape_z.index.to_period("M")

    dxy = monthly_last(dxy_close).rename("DXY")
    tyx = monthly_last(tyx_close).rename("30Y")
    if float(tyx.median()) > 20:
        tyx = tyx / 10.0

    by_period = pd.concat(
        {
            "TQQQ_Z": cape_z,
            "GLD_Z": -log_signal(dxy),
            "TLT_Z": -log_signal(tyx),
        },
        axis=1,
    ).sort_index()
    for asset in ("TQQQ", "GLD", "TLT"):
        by_period[f"{asset}_Recommendation"] = 2 * norm.cdf(-by_period[f"{asset}_Z"])

    last_trade_by_period = pd.Series(trading_dates, index=trading_dates.to_period("M")).groupby(level=0).max()
    by_period = by_period.loc[by_period.index.intersection(last_trade_by_period.index)]
    by_period.index = pd.DatetimeIndex(last_trade_by_period.loc[by_period.index].to_numpy())
    return by_period.sort_index()


def build_daily_profit_signals(
    monthly_shiller: pd.DataFrame,
    cape_daily: pd.DataFrame,
    dxy_close: pd.Series,
    tyx_close: pd.Series,
    trading_dates: pd.DatetimeIndex,
) -> pd.DataFrame:
    """Build daily Z-scores using 119 completed months plus today's value."""
    dates = pd.DatetimeIndex(trading_dates).sort_values()

    daily_cape = cape_daily["CAPE_daily"].reindex(dates)
    cape_z = compute_point_in_time_daily_z(
        daily_cape, monthly_shiller["CAPE"], window=120
    )

    dxy_daily = pd.to_numeric(dxy_close, errors="coerce").reindex(dates).ffill()
    dxy_monthly = monthly_last(dxy_close).rename("DXY")
    dxy_z = compute_point_in_time_daily_z(
        log_transform(dxy_daily), log_transform(dxy_monthly), window=120
    )

    tyx_daily = pd.to_numeric(tyx_close, errors="coerce").reindex(dates).ffill()
    tyx_monthly = monthly_last(tyx_close).rename("30Y")
    if float(tyx_monthly.median()) > 20:
        tyx_daily = tyx_daily / 10.0
        tyx_monthly = tyx_monthly / 10.0
    tyx_z = compute_point_in_time_daily_z(
        log_transform(tyx_daily), log_transform(tyx_monthly), window=120
    )

    signals = pd.concat(
        {"TQQQ_Z": cape_z, "GLD_Z": -dxy_z, "TLT_Z": -tyx_z},
        axis=1,
    ).reindex(dates)
    signals["CAPE_Daily"] = daily_cape
    signals["DXY_Daily"] = dxy_daily
    signals["30Y_Daily"] = tyx_daily
    for asset in ("TQQQ", "GLD", "TLT"):
        signals[f"{asset}_Risk"] = norm.cdf(signals[f"{asset}_Z"])
    return signals


def curve_summary(curve: pd.Series) -> dict[str, float | str]:
    curve = curve.dropna()
    years = (curve.index[-1] - curve.index[0]).days / 365.2425
    drawdown = curve / curve.cummax() - 1
    return {
        "Start_Date": curve.index[0].date().isoformat(),
        "End_Date": curve.index[-1].date().isoformat(),
        "Ending_Equity": float(curve.iloc[-1]),
        "CAGR": float((curve.iloc[-1] / curve.iloc[0]) ** (1 / years) - 1),
        "Maximum_Drawdown": float(drawdown.min()),
        "Maximum_Drawdown_Date": drawdown.idxmin().date().isoformat(),
    }


def monthly_rebalanced_curve(total_return_prices: pd.DataFrame, initial: float) -> pd.Series:
    prices = total_return_prices.dropna()
    returns = prices.pct_change().fillna(0.0)
    target = np.array([0.60, 0.30, 0.10])
    weights = target.copy()
    wealth = initial
    values = []
    prior_period = None
    for date, row in returns.iterrows():
        period = date.to_period("M")
        if prior_period is not None and period != prior_period:
            weights = target.copy()
        asset_returns = row.to_numpy(dtype=float)
        portfolio_return = float(weights @ asset_returns)
        wealth *= 1 + portfolio_return
        gross_weights = weights * (1 + asset_returns)
        weights = gross_weights / gross_weights.sum()
        values.append(wealth)
        prior_period = period
    return pd.Series(values, index=prices.index, name="Rebalanced_60_30_10")


def main() -> None:
    yf.cache.set_cache_location(tempfile.mkdtemp(prefix="portfolio-backtest-yf-"))
    downloaded: dict[str, tuple[pd.DataFrame, pd.DataFrame]] = {}
    for symbol, start in {
        "QQQ": "1999-03-01",
        "TQQQ": "2010-02-01",
        "GLD": "2004-11-01",
        "TLT": "2002-07-01",
        "^VIX": "1990-01-01",
        "DX-Y.NYB": START,
        "^TYX": START,
        "^GSPC": START,
    }.items():
        downloaded[symbol] = download_yahoo(symbol, start)

    qqq_raw, qqq_adjusted = downloaded["QQQ"]
    tqqq_raw, tqqq_adjusted = downloaded["TQQQ"]
    gld_raw, gld_adjusted = downloaded["GLD"]
    tlt_raw, tlt_adjusted = downloaded["TLT"]
    vix_raw, _ = downloaded["^VIX"]
    dxy_raw, _ = downloaded["DX-Y.NYB"]
    tyx_raw, _ = downloaded["^TYX"]
    spx_raw, _ = downloaded["^GSPC"]

    tqqq_trade, tqqq_total_close = build_spliced_tqqq(
        qqq_adjusted, tqqq_raw, tqqq_adjusted
    )
    prices = {
        "TQQQ": tqqq_trade,
        "GLD": trade_frame(gld_raw),
        "TLT": trade_frame(tlt_raw),
    }
    common_dates = prices["TQQQ"].index
    for frame in prices.values():
        common_dates = common_dates.intersection(frame.index)

    monthly_shiller = get_shiller_monthly(spx_raw["Close"])
    cape = monthly_shiller["CAPE"]
    cape_daily = build_daily_cape(monthly_shiller, spx_raw["Close"])
    monthly_signals = build_monthly_signals(
        cape,
        dxy_raw["Close"],
        tyx_raw["Close"],
        common_dates,
    )
    daily_profit_signals = build_daily_profit_signals(
        monthly_shiller,
        cape_daily,
        dxy_raw["Close"],
        tyx_raw["Close"],
        common_dates,
    )
    vix_daily = vix_raw[["High", "Close"]].dropna().rename(
        columns={"High": "VIX_High", "Close": "VIX_Close"}
    )
    classified, events, event_signals = detect_vix_wave_signals(vix_daily)

    engine = PortfolioBacktester(
        prices,
        monthly_signals,
        daily_profit_signals,
        classified,
        events,
        event_signals,
        config=BacktestConfig(),
    )
    result = engine.run()
    equity = result["equity"]
    start = equity.index[0]

    qqq_curve = qqq_adjusted["Close"].reindex(equity.index).ffill().dropna()
    qqq_curve = qqq_curve / qqq_curve.iloc[0] * 10_000
    tqqq_curve = tqqq_total_close.reindex(equity.index).ffill().dropna()
    tqqq_curve = tqqq_curve / tqqq_curve.iloc[0] * 10_000
    total_return_prices = pd.concat(
        [
            tqqq_total_close.rename("TQQQ"),
            gld_adjusted["Close"].rename("GLD"),
            tlt_adjusted["Close"].rename("TLT"),
        ],
        axis=1,
    ).loc[start:].dropna()
    rebalanced_curve = monthly_rebalanced_curve(total_return_prices, 10_000)

    summary = {
        "Strategy": result["summary"],
        "Benchmarks": {
            "QQQ_Buy_And_Hold": curve_summary(qqq_curve),
            "TQQQ_Buy_And_Hold": curve_summary(tqqq_curve),
            "Monthly_Rebalanced_60_30_10": curve_summary(rebalanced_curve),
        },
        "Data": {
            "First_Complete_Signal_Date": monthly_signals.dropna(
                subset=["TQQQ_Z", "GLD_Z", "TLT_Z"]
            ).index[0].date().isoformat(),
            "VIX_Event_Count": int(len(events)),
            "VIX_Wave_Signal_Count": int(len(event_signals)),
            "Dividend_Timing": "Yahoo ex-date (payment dates unavailable)",
            "Daily_CAPE_Method": "SPX close / prior-month Shiller E10",
            "Shiller_Monthly_Source": SHILLER_API,
        },
    }

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    equity.to_csv(REPORT_DIR / "equity_curve.csv")
    result["transactions"].to_csv(REPORT_DIR / "transactions.csv", index=False)
    result["decisions"].to_csv(REPORT_DIR / "monthly_decisions.csv", index=False)
    events.to_csv(REPORT_DIR / "vix_events.csv", index=False)
    event_signals.to_csv(REPORT_DIR / "vix_wave_signals.csv", index=False)
    monthly_signals.to_csv(REPORT_DIR / "valuation_signals.csv")
    daily_profit_signals.to_csv(REPORT_DIR / "daily_profit_signals.csv")
    cape_daily.to_csv(REPORT_DIR / "cape_daily.csv")
    (REPORT_DIR / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    chart = pd.concat(
        [
            equity["Total_Equity"].rename("Strategy"),
            qqq_curve.rename("QQQ buy-and-hold"),
            tqqq_curve.rename("TQQQ buy-and-hold"),
            rebalanced_curve,
        ],
        axis=1,
    ).dropna(how="all")
    ax = chart.plot(figsize=(14, 7), logy=True, title="Portfolio backtest equity curves")
    ax.set_ylabel("Equity, USD, log scale")
    ax.grid(alpha=0.25)
    ax.figure.tight_layout()
    ax.figure.savefig(REPORT_DIR / "equity_curves.png", dpi=160)
    plt.close(ax.figure)

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"Reports: {REPORT_DIR}")


if __name__ == "__main__":
    main()
