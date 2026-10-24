import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.data import load_data
from app import logic
from datetime import date

fc, act = load_data()
df = logic.evaluation(fc, act, date(2026, 1, 2), date(2026, 2, 1), "09:00")

print("bias share of positive errors:", (df.error > 0).mean())
print("MAE after removing mean bias:", (df.error - df.error.mean()).abs().mean())
df["actual_bin"] = pd.cut(df.actual, [0, 5000, 10000, 15000, 25000])
print(df.groupby("actual_bin", observed=True).agg(n=("error", "size"), bias=("error", "mean"), mae=("abs_error", "mean")))
print("corr(forecast, actual):", df.forecast.corr(df.actual))
print(df.groupby(df.startTime.dt.date).error.mean().describe())