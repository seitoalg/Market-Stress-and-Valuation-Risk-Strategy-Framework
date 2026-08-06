"""Event-driven portfolio engine for the agreed TQQQ/GLD/TLT strategy."""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt

import numpy as np
import pandas as pd

from src.market_risk.vix import classify_vix_stress_events


ASSETS = ("TQQQ", "GLD", "TLT")


@dataclass(frozen=True)
class BacktestConfig:
    initial_cash: float = 10_000.0
    target_weights: tuple[float, float, float] = (0.60, 0.30, 0.10)
    convergence_months: float = 18.3
    slippage_bps: float = 5.0
    event_tranches: int = 3

    def target_map(self) -> dict[str, float]:
        return dict(zip(ASSETS, self.target_weights, strict=True))


def _wma(series: pd.Series, window: int) -> pd.Series:
    weights = np.arange(1, window + 1, dtype=float)
    return series.rolling(window).apply(
        lambda values: float(np.dot(values, weights) / weights.sum()),
        raw=True,
    )


def detect_vix_wave_signals(
    vix_daily: pd.DataFrame,
    *,
    window_months: int = 360,
    max_buys_per_event: int = 3,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return canonical VIX classifications, events, and WMA wave signals."""
    classified, events = classify_vix_stress_events(
        vix_daily,
        high_col="VIX_High",
        window_months=window_months,
        exit_consecutive_days=10,
    )
    high = classified["VIX_High"]
    classified["WMA_5"] = _wma(high, 5)
    classified["WMA_10"] = _wma(high, 10)
    classified["WMA_Cross_Down"] = (
        classified["WMA_5"].lt(classified["WMA_10"])
        & classified["WMA_5"].shift(1).ge(classified["WMA_10"].shift(1))
    )
    classified["Below_2_Sigma"] = classified["VIX_High"].lt(
        classified["+2_Sigma"]
    )

    records: list[dict[str, object]] = []
    for event_id, rows in classified.dropna(subset=["Event_ID"]).groupby("Event_ID"):
        armed = True
        waiting_wave_end = False
        below_two_count = 0
        buy_count = 0
        last_signal_date: pd.Timestamp | None = None

        for date, row in rows.iterrows():
            above_two = bool(row["Above_2_Sigma"])
            below_two = bool(row["Below_2_Sigma"])
            cross_down = bool(row["WMA_Cross_Down"])

            if armed and cross_down and buy_count < max_buys_per_event:
                buy_count += 1
                last_signal_date = date
                records.append(
                    {
                        "Event_ID": int(event_id),
                        "Wave": buy_count,
                        "Signal_Date": date,
                        "Signal_Type": (
                            "Above +2 sigma, fear-zone reversal"
                            if above_two
                            else "Below +2 sigma, post-shock confirmation"
                        ),
                        "VIX_High": float(row["VIX_High"]),
                        "Signal_Z": float(
                            (row["VIX_High"] - row["Mean_Long_Run"])
                            / row["Std_Long_Run"]
                        ),
                    }
                )
                armed = False
                waiting_wave_end = True
                below_two_count = 0

            if waiting_wave_end and last_signal_date is not None and date > last_signal_date:
                below_two_count = below_two_count + 1 if below_two else 0
                if below_two_count >= 5:
                    waiting_wave_end = False
                    below_two_count = 0

            if (
                not armed
                and not waiting_wave_end
                and above_two
                and buy_count < max_buys_per_event
            ):
                armed = True

    signals = pd.DataFrame(records)
    if not signals.empty:
        signals = signals.merge(
            events[["Event_ID", "Event_Start_Date", "Event_End_Date"]],
            on="Event_ID",
            how="left",
        )
    return classified, events, signals


class PortfolioBacktester:
    """Run the agreed strategy against supplied point-in-time market data."""

    def __init__(
        self,
        prices: dict[str, pd.DataFrame],
        monthly_signals: pd.DataFrame,
        daily_profit_signals: pd.DataFrame,
        vix_classified: pd.DataFrame,
        vix_events: pd.DataFrame,
        vix_signals: pd.DataFrame,
        *,
        config: BacktestConfig | None = None,
    ) -> None:
        self.config = config or BacktestConfig()
        self.targets = self.config.target_map()
        self.prices = {asset: frame.sort_index().copy() for asset, frame in prices.items()}
        missing = set(ASSETS).difference(self.prices)
        if missing:
            raise KeyError(f"missing asset prices: {sorted(missing)}")
        for asset, frame in self.prices.items():
            required = {"Open", "Close", "Dividend"}
            if not required.issubset(frame.columns):
                raise KeyError(f"{asset} missing columns: {sorted(required-set(frame.columns))}")

        self.monthly_signals = monthly_signals.sort_index().copy()
        self.daily_profit_signals = daily_profit_signals.sort_index().copy()
        self.vix_classified = vix_classified.sort_index().copy()
        self.vix_events = vix_events.copy()
        self.vix_signals = vix_signals.copy()

        valid_signal_rows = self.monthly_signals.dropna(
            subset=[f"{asset}_Z" for asset in ASSETS]
        )
        if valid_signal_rows.empty:
            raise ValueError("monthly valuation signals contain no complete rows")
        self.start_date = pd.Timestamp(valid_signal_rows.index[0])
        self.dates = self._master_dates(self.start_date)
        if self.dates.empty:
            raise ValueError("no trading dates at or after first complete signal")

        self.cash = float(self.config.initial_cash)
        self.shares = {asset: 0.0 for asset in ASSETS}
        self.lots: dict[str, list[dict[str, object]]] = {asset: [] for asset in ASSETS}
        self.orders: dict[pd.Timestamp, list[dict[str, object]]] = {}
        self.event_budgets: dict[int, float] = {}
        self.tier_fired = {asset: set() for asset in ASSETS}
        self.previous_z = {asset: np.nan for asset in ASSETS}
        self.transaction_records: list[dict[str, object]] = []
        self.decision_records: list[dict[str, object]] = []
        self.equity_records: list[dict[str, object]] = []

        self.event_starts = self._event_start_map()
        self.event_signal_map = self._event_signal_map()
        self.monthly_signal_map = {
            pd.Timestamp(date): row for date, row in self.monthly_signals.iterrows()
        }
        self.daily_profit_signal_map = {
            pd.Timestamp(date): row
            for date, row in self.daily_profit_signals.iterrows()
        }
        self.suspended_periods = self._suspended_months()

    def _master_dates(self, start: pd.Timestamp) -> pd.DatetimeIndex:
        common = None
        for frame in self.prices.values():
            idx = frame.index
            common = idx if common is None else common.intersection(idx)
        return pd.DatetimeIndex(common[common >= start]).sort_values()

    def _event_start_map(self) -> dict[pd.Timestamp, list[int]]:
        mapping: dict[pd.Timestamp, list[int]] = {}
        for _, row in self.vix_events.iterrows():
            date = pd.Timestamp(row["Event_Start_Date"])
            mapping.setdefault(date, []).append(int(row["Event_ID"]))
        return mapping

    def _event_signal_map(self) -> dict[pd.Timestamp, list[dict[str, object]]]:
        mapping: dict[pd.Timestamp, list[dict[str, object]]] = {}
        for _, row in self.vix_signals.iterrows():
            date = pd.Timestamp(row["Signal_Date"])
            mapping.setdefault(date, []).append(row.to_dict())
        return mapping

    def _suspended_months(self) -> set[pd.Period]:
        periods: set[pd.Period] = set()
        if not self.vix_signals.empty:
            periods.update(
                pd.to_datetime(self.vix_signals["Signal_Date"]).dt.to_period("M")
            )
        if not self.vix_classified.empty:
            for period, rows in self.vix_classified.groupby(
                self.vix_classified.index.to_period("M")
            ):
                if bool(rows.iloc[-1]["In_Stress_Event"]):
                    periods.add(period)
        return periods

    def _next_trading_date(self, date: pd.Timestamp) -> pd.Timestamp | None:
        position = self.dates.searchsorted(date, side="right")
        return None if position >= len(self.dates) else self.dates[position]

    def _queue(self, date: pd.Timestamp | None, order: dict[str, object]) -> None:
        if date is not None:
            self.orders.setdefault(date, []).append(order)

    def _price(self, asset: str, date: pd.Timestamp, field: str) -> float:
        return float(self.prices[asset].at[date, field])

    def _equity(self, date: pd.Timestamp, field: str = "Close") -> float:
        return self.cash + sum(
            self.shares[asset] * self._price(asset, date, field) for asset in ASSETS
        )

    def _credit_dividends(self, date: pd.Timestamp) -> None:
        for asset in ASSETS:
            amount = self._price(asset, date, "Dividend")
            if amount <= 0 or self.shares[asset] <= 0:
                continue
            cash_amount = self.shares[asset] * amount
            self.cash += cash_amount
            self.transaction_records.append(
                {
                    "Date": date,
                    "Asset": asset,
                    "Action": "DIVIDEND",
                    "Reason": "cash_distribution",
                    "Shares": self.shares[asset],
                    "Price": amount,
                    "Cash_Amount": cash_amount,
                    "Realized_PnL": cash_amount,
                }
            )

    def _execute_buy(self, date: pd.Timestamp, order: dict[str, object]) -> None:
        asset = str(order["Asset"])
        requested = float(order["Amount"])
        amount = min(requested, self.cash)
        if amount <= 1e-10:
            return
        price = self._price(asset, date, "Open") * (
            1 + self.config.slippage_bps / 10_000
        )
        shares = amount / price
        self.cash -= amount
        self.shares[asset] += shares
        self.lots[asset].append(
            {
                "Date": date,
                "Shares": shares,
                "Cost_Per_Share": price,
                "Reason": order["Reason"],
            }
        )
        self.transaction_records.append(
            {
                "Date": date,
                "Asset": asset,
                "Action": "BUY",
                "Reason": order["Reason"],
                "Shares": shares,
                "Price": price,
                "Cash_Amount": -amount,
                "Realized_PnL": 0.0,
                "Event_ID": order.get("Event_ID"),
                "Wave": order.get("Wave"),
                "Signal_Date": order.get("Signal_Date"),
            }
        )

    def _execute_sell(self, date: pd.Timestamp, order: dict[str, object]) -> None:
        asset = str(order["Asset"])
        open_price = self._price(asset, date, "Open")
        sell_price = open_price * (1 - self.config.slippage_bps / 10_000)
        equity = self._equity(date, "Open")
        market_value = self.shares[asset] * open_price
        excess = max(0.0, market_value - self.targets[asset] * equity)
        requested_value = excess * float(order["Fraction"])
        if requested_value <= 1e-10:
            return

        remaining_shares = requested_value / sell_price
        realized = 0.0
        sold_shares = 0.0
        for lot in self.lots[asset]:
            available = float(lot["Shares"])
            cost = float(lot["Cost_Per_Share"])
            if available <= 0 or sell_price <= cost:
                continue
            quantity = min(available, remaining_shares)
            lot["Shares"] = available - quantity
            remaining_shares -= quantity
            sold_shares += quantity
            realized += quantity * (sell_price - cost)
            if remaining_shares <= 1e-12:
                break

        if sold_shares <= 0:
            return
        proceeds = sold_shares * sell_price
        self.shares[asset] -= sold_shares
        self.cash += proceeds
        self.lots[asset] = [lot for lot in self.lots[asset] if float(lot["Shares"]) > 1e-12]
        self.transaction_records.append(
            {
                "Date": date,
                "Asset": asset,
                "Action": "SELL",
                "Reason": order["Reason"],
                "Shares": -sold_shares,
                "Price": sell_price,
                "Cash_Amount": proceeds,
                "Realized_PnL": realized,
                "Sigma_Tier": order.get("Tier"),
                "Signal_Date": order.get("Signal_Date"),
            }
        )

    def _execute_orders(self, date: pd.Timestamp) -> None:
        orders = self.orders.pop(date, [])
        priority = {"profit_take": 0, "vix_event": 1, "normal_monthly": 2}
        for order in sorted(orders, key=lambda item: priority[str(item["Reason"])]):
            if order["Reason"] == "profit_take":
                self._execute_sell(date, order)
            else:
                self._execute_buy(date, order)

    def _freeze_event_budgets(self, date: pd.Timestamp) -> None:
        for event_id in self.event_starts.get(date, []):
            self.event_budgets[event_id] = self.cash

    def _schedule_event_orders(self, date: pd.Timestamp) -> None:
        execute_date = self._next_trading_date(date)
        for signal in self.event_signal_map.get(date, []):
            event_id = int(signal["Event_ID"])
            if event_id not in self.event_budgets:
                self.event_budgets[event_id] = self.cash
            amount = self.event_budgets[event_id] / self.config.event_tranches
            self._queue(
                execute_date,
                {
                    "Asset": "TQQQ",
                    "Amount": amount,
                    "Reason": "vix_event",
                    "Event_ID": event_id,
                    "Wave": int(signal["Wave"]),
                    "Signal_Date": date,
                },
            )

    def _schedule_profit_taking(
        self, date: pd.Timestamp, row: pd.Series
    ) -> None:
        execute_date = self._next_trading_date(date)
        for asset in ASSETS:
            z = float(row[f"{asset}_Z"])
            previous = self.previous_z[asset]
            if z <= 0:
                self.tier_fired[asset].clear()

            crossed = [
                tier
                for tier in (1, 2, 3)
                if pd.notna(previous) and previous < tier <= z
            ]
            for tier in crossed:
                if tier not in self.tier_fired[asset]:
                    fraction = {1: 0.25, 2: 0.50, 3: 1.00}[tier]
                    self._queue(
                        execute_date,
                        {
                            "Asset": asset,
                            "Fraction": fraction,
                            "Reason": "profit_take",
                            "Tier": tier,
                            "Signal_Date": date,
                        },
                    )
                    self.tier_fired[asset].add(tier)
            self.previous_z[asset] = z

    def _schedule_normal_buys(self, date: pd.Timestamp, row: pd.Series) -> None:
        period = date.to_period("M")
        if period in self.suspended_periods:
            self.decision_records.append(
                {"Signal_Date": date, "Suspended": True, "Cash": self.cash}
            )
            return

        equity = self._equity(date, "Close")
        amounts: dict[str, float] = {}
        decision: dict[str, object] = {
            "Signal_Date": date,
            "Suspended": False,
            "Cash": self.cash,
            "Total_Equity": equity,
        }
        for asset in ASSETS:
            market_value = self.shares[asset] * self._price(asset, date, "Close")
            current_weight = market_value / equity
            gap = max(0.0, self.targets[asset] - current_weight)
            recommendation = float(row[f"{asset}_Recommendation"])
            amounts[asset] = (
                equity * gap / self.config.convergence_months * recommendation
            )
            decision[f"{asset}_Weight"] = current_weight
            decision[f"{asset}_Gap"] = gap
            decision[f"{asset}_Z"] = float(row[f"{asset}_Z"])
            decision[f"{asset}_Recommendation"] = recommendation
            decision[f"{asset}_Requested_Buy"] = amounts[asset]

        total = sum(amounts.values())
        if total >= self.cash and total > 0:
            scale = self.cash * (1 - 1e-9) / total
            amounts = {asset: amount * scale for asset, amount in amounts.items()}
            decision["Cash_Scale"] = scale
        else:
            decision["Cash_Scale"] = 1.0

        execute_date = self._next_trading_date(date)
        for asset, amount in amounts.items():
            self._queue(
                execute_date,
                {
                    "Asset": asset,
                    "Amount": amount,
                    "Reason": "normal_monthly",
                    "Signal_Date": date,
                },
            )
        self.decision_records.append(decision)

    def _record_equity(self, date: pd.Timestamp) -> None:
        equity = self._equity(date, "Close")
        record: dict[str, object] = {
            "Date": date,
            "Cash": self.cash,
            "Total_Equity": equity,
            "Cash_Weight": self.cash / equity,
        }
        for asset in ASSETS:
            value = self.shares[asset] * self._price(asset, date, "Close")
            record[f"{asset}_Shares"] = self.shares[asset]
            record[f"{asset}_Value"] = value
            record[f"{asset}_Weight"] = value / equity
        self.equity_records.append(record)

    def run(self) -> dict[str, object]:
        for date in self.dates:
            self._credit_dividends(date)
            self._execute_orders(date)
            self._freeze_event_budgets(date)
            self._schedule_event_orders(date)

            daily_row = self.daily_profit_signal_map.get(date)
            if daily_row is not None and daily_row[
                [f"{asset}_Z" for asset in ASSETS]
            ].notna().all():
                self._schedule_profit_taking(date, daily_row)

            monthly_row = self.monthly_signal_map.get(date)
            if monthly_row is not None and monthly_row[
                [f"{asset}_Z" for asset in ASSETS]
            ].notna().all():
                self._schedule_normal_buys(date, monthly_row)
            self._record_equity(date)

        equity = pd.DataFrame(self.equity_records).set_index("Date")
        transactions = pd.DataFrame(self.transaction_records)
        decisions = pd.DataFrame(self.decision_records)
        return {
            "equity": equity,
            "transactions": transactions,
            "decisions": decisions,
            "summary": self.summarize(equity, transactions),
        }

    @staticmethod
    def summarize(equity: pd.DataFrame, transactions: pd.DataFrame) -> dict[str, object]:
        start = equity.index[0]
        end = equity.index[-1]
        years = (end - start).days / 365.2425
        ending = float(equity["Total_Equity"].iloc[-1])
        initial = float(equity["Total_Equity"].iloc[0])
        cagr = (ending / initial) ** (1 / years) - 1 if years > 0 else np.nan
        returns = equity["Total_Equity"].pct_change().dropna()
        drawdown = equity["Total_Equity"] / equity["Total_Equity"].cummax() - 1
        annual_vol = float(returns.std(ddof=1) * sqrt(252))
        sharpe = float(returns.mean() / returns.std(ddof=1) * sqrt(252))
        if returns.std(ddof=1) == 0:
            sharpe = np.nan
        action_counts = (
            transactions.groupby(["Action", "Reason"]).size().to_dict()
            if not transactions.empty
            else {}
        )
        return {
            "Start_Date": start.date().isoformat(),
            "End_Date": end.date().isoformat(),
            "Initial_Equity": initial,
            "Ending_Equity": ending,
            "CAGR": float(cagr),
            "Maximum_Drawdown": float(drawdown.min()),
            "Maximum_Drawdown_Date": drawdown.idxmin().date().isoformat(),
            "Annualized_Volatility": annual_vol,
            "Sharpe_Zero_Cash_Rate": sharpe,
            "Average_Cash_Weight": float(equity["Cash_Weight"].mean()),
            "Minimum_Cash": float(equity["Cash"].min()),
            "Realized_Profit": (
                float(transactions["Realized_PnL"].sum())
                if not transactions.empty
                else 0.0
            ),
            "Action_Counts": {f"{a}:{r}": int(v) for (a, r), v in action_counts.items()},
        }
