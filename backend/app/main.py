from datetime import date
from functools import lru_cache
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import logic
from .data import load_data

FC, ACT = load_data()
FIRST, LAST = date(2026, 1, 2), date(2026, 2, 1)

app = FastAPI(title="Wind forecast portal")


@lru_cache(maxsize=64)
def _eval(cutoff: str):
    return logic.evaluation(FC, ACT, FIRST, LAST, cutoff)


@app.get("/api/forecast")
def forecast(day: date, cutoff: str = "09:00"):
    if not (FIRST <= day <= LAST):
        raise HTTPException(400, f"day must be between {FIRST} and {LAST}")
    d0 = pd.Timestamp(day, tz="UTC")  # January: UK time == UTC
    a = ACT[(ACT.startTime >= d0) & (ACT.startTime < d0 + pd.Timedelta(days=1))]
    f = logic.forecast_for_day(FC, day, cutoff)
    g = a.merge(f, on="startTime", how="outer").sort_values("startTime")

    s = logic.summarise(_eval(cutoff))
    g["lo"] = (g.forecast - s.get("err_q90", 0.0)).clip(lower=0)
    g["hi"] = g.forecast - s.get("err_q10", 0.0)

    publish = g.publishTime.max()
    g["startTime"] = g.startTime.dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    g["publishTime"] = g.publishTime.dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "cutoff_utc": logic.decision_cutoff(day, cutoff).isoformat(),
        "publish_time": None if pd.isna(publish) else publish.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "band_mw": s.get("p90_abs", 0.0),
        "points": g.astype(object).where(g.notna(), None).to_dict("records"),
    }


@app.get("/api/metrics")
def metrics(cutoff: str = "09:00"):
    df = _eval(cutoff)
    return {"summary": logic.summarise(df), "by_hour": logic.by_hour(df)}



@app.get("/api/daily-errors")
def daily(cutoff: str = "09:00"):
    return logic.daily_errors(_eval(cutoff))

@app.get("/api/horizon-errors")
def horizon():
    return logic.horizon_errors(FC, ACT)


# serve built React app (present in Docker image)
DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}")
    def spa(path: str):
        return FileResponse(DIST / "index.html")