"""Download January 2026 wind actuals (FUELHH) and forecasts (WINDFOR) to parquet."""
import time
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests

BASE = "https://data.elexon.co.uk/bmrs/api/v1/datasets"
OUT = Path(__file__).resolve().parents[1] / "data"


def get_json(url: str, params: dict, retries: int = 6):
    for i in range(retries):
        r = requests.get(url, params=params, timeout=90)
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(2 ** i)
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError(f"Failed after retries: {url} {params}")


def fetch_actuals(start: date, end: date) -> pd.DataFrame:
    rows, d = [], start
    while d <= end:
        chunk_end = min(d + timedelta(days=6), end)
        rows += get_json(f"{BASE}/FUELHH/stream", {
            "settlementDateFrom": d.isoformat(),
            "settlementDateTo": chunk_end.isoformat(),
            "fuelType": ["WIND"],
        })
        d = chunk_end + timedelta(days=1)
        time.sleep(0.5)
    df = pd.DataFrame(rows)
    df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    df = df[["startTime", "generation"]].drop_duplicates("startTime").sort_values("startTime")
    return df.rename(columns={"generation": "actual"})


def fetch_forecasts(start: date, end: date) -> pd.DataFrame:
    rows, d = [], start
    while d <= end:
        rows += get_json(f"{BASE}/WINDFOR/stream", {
            "publishDateTimeFrom": f"{d.isoformat()}T00:00:00Z",
            "publishDateTimeTo": f"{(d + timedelta(days=1)).isoformat()}T00:00:00Z",
        })
        d += timedelta(days=1)
        time.sleep(0.5)
    df = pd.DataFrame(rows)
    for c in ("startTime", "publishTime"):
        df[c] = pd.to_datetime(df[c], utc=True)
    df = df[["startTime", "publishTime", "generation"]]
    df = df.drop_duplicates(["startTime", "publishTime"]).sort_values(["startTime", "publishTime"])
    return df.rename(columns={"generation": "forecast"})


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    # Delivery days 2 Jan - 1 Feb (decisions made in January); forecasts published from late Dec
    act = fetch_actuals(date(2026, 1, 1), date(2026, 2, 2))
    fc = fetch_forecasts(date(2025, 12, 28), date(2026, 2, 1))
    act.to_csv(OUT / "actuals.csv", index=False)
    fc.to_csv(OUT / "forecasts.csv", index=False)
    print("actuals", act.shape, act.startTime.min(), act.startTime.max())
    print("forecasts", fc.shape, fc.publishTime.min(), fc.publishTime.max())
    print("horizon hours:", ((fc.startTime - fc.publishTime).dt.total_seconds() / 3600).describe())