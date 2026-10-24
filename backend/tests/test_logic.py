from datetime import date
import pandas as pd
from app.logic import decision_cutoff, forecast_for_day


def mk(rows):
    df = pd.DataFrame(rows, columns=["startTime", "publishTime", "forecast"])
    df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    df["publishTime"] = pd.to_datetime(df["publishTime"], utc=True)
    return df


def test_cutoff_is_day_before_0900_utc_in_january():
    assert decision_cutoff(date(2026, 1, 10), "09:00") == pd.Timestamp("2026-01-09T09:00Z")


def test_picks_latest_before_cutoff():
    t = "2026-01-10T12:00:00Z"
    fc = mk([[t, "2026-01-09T06:00:00Z", 100.0],
             [t, "2026-01-09T08:00:00Z", 200.0],   # expected
             [t, "2026-01-09T10:00:00Z", 300.0]])  # after cutoff -> ignored
    out = forecast_for_day(fc, date(2026, 1, 10))
    assert out.forecast.tolist() == [200.0]


def test_ignores_other_days_and_empty_ok():
    fc = mk([["2026-01-11T00:00:00Z", "2026-01-09T06:00:00Z", 1.0]])
    assert forecast_for_day(fc, date(2026, 1, 10)).empty