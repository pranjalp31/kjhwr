from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    fc = pd.read_csv(DATA_DIR / "forecasts.csv")
    act = pd.read_csv(DATA_DIR / "actuals.csv")
    for df, cols in ((fc, ["startTime", "publishTime"]), (act, ["startTime"])):
        for c in cols:
            df[c] = pd.to_datetime(df[c], utc=True)
    return fc, act