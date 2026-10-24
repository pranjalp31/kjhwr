from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

LONDON = ZoneInfo("Europe/London")


def decision_cutoff(day: date, cutoff_hhmm: str = "09:00") -> pd.Timestamp:
    """Decision time for delivery `day`: cutoff_hhmm UK time on day-1, as UTC."""
    h, m = map(int, cutoff_hhmm.split(":"))
    d1 = day - timedelta(days=1)
    local = datetime(d1.year, d1.month, d1.day, h, m, tzinfo=LONDON)
    return pd.Timestamp(local).tz_convert("UTC")


def forecast_for_day(fc: pd.DataFrame, day: date, cutoff_hhmm: str = "09:00") -> pd.DataFrame:
    """For each half-hour of `day`, the latest forecast published at or before the cutoff."""
    start = pd.Timestamp(datetime(day.year, day.month, day.day, tzinfo=LONDON)).tz_convert("UTC")
    end = pd.Timestamp(
        datetime(day.year, day.month, day.day, tzinfo=LONDON) + timedelta(days=1)
    ).tz_convert("UTC")
    cutoff = decision_cutoff(day, cutoff_hhmm)
    sel = fc[(fc.startTime >= start) & (fc.startTime < end) & (fc.publishTime <= cutoff)]
    sel = sel.sort_values("publishTime").drop_duplicates("startTime", keep="last")
    return sel.sort_values("startTime").reset_index(drop=True)


def evaluation(fc, act, start: date, end: date, cutoff_hhmm="09:00") -> pd.DataFrame:
    days = pd.date_range(start, end, freq="D").date
    parts = [forecast_for_day(fc, d, cutoff_hhmm) for d in days]
    df = pd.concat(parts, ignore_index=True).merge(act, on="startTime", how="inner")
    df["error"] = df.forecast - df.actual          # + means over-forecast
    df["abs_error"] = df.error.abs()
    df["horizon_h"] = (df.startTime - df.publishTime).dt.total_seconds() / 3600
    return df


def summarise(df: pd.DataFrame) -> dict:
    if df.empty:
        return {}
    return {
        "n": int(len(df)),
        "mae": float(df.abs_error.mean()),
        "rmse": float(np.sqrt((df.error ** 2).mean())),
        "bias": float(df.error.mean()),
        "p50_abs": float(df.abs_error.quantile(0.5)),
        "p90_abs": float(df.abs_error.quantile(0.9)),
        "p99_abs": float(df.abs_error.quantile(0.99)),
        "mean_actual": float(df.actual.mean()),
        "mae_pct_of_mean": float(df.abs_error.mean() / df.actual.mean() * 100),
        "err_q10": float(df.error.quantile(0.10)),
        "err_q90": float(df.error.quantile(0.90)),
        "pct_over": float((df.error > 0).mean() * 100),
    }


def by_hour(df: pd.DataFrame) -> list[dict]:
    g = df.assign(hour=df.startTime.dt.tz_convert(LONDON).dt.hour).groupby("hour")
    return [{"hour": int(h), "mae": float(x.abs_error.mean()), "bias": float(x.error.mean())} for h, x in g]


def horizon_errors(fc, act, bin_h: int = 6) -> list[dict]:
    """Error vs. forecast horizon using ALL forecasts (not just the decision-time one)."""
    df = fc.merge(act, on="startTime")
    df["horizon_h"] = (df.startTime - df.publishTime).dt.total_seconds() / 3600
    df = df[df.horizon_h >= 0]
    df["bin"] = (df.horizon_h // bin_h * bin_h).astype(int)
    df["abs_error"] = (df.forecast - df.actual).abs()
    g = df.groupby("bin").abs_error
    return [{"horizon_from": int(b), "horizon_to": int(b + bin_h),
             "mae": float(s.mean()), "p90": float(s.quantile(0.9))} for b, s in g]

def daily_errors(df: pd.DataFrame) -> list[dict]:
    g = df.groupby(df.startTime.dt.tz_convert(LONDON).dt.date)
    return [{"day": str(d), "mae": float(x.abs_error.mean()), "bias": float(x.error.mean())} for d, x in g]