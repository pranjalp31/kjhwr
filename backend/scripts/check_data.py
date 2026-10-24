import sys
from pathlib import Path
from datetime import date

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.logic import forecast_for_day

from app.data import load_data

fc, _ = load_data()

print("Publish interval (most common gaps):")
print(fc.publishTime.drop_duplicates().sort_values().diff().value_counts().head())

for cutoff in ("09:00",):
    print(f"\nCutoff {cutoff}")
    for d in pd.date_range("2026-01-02", "2026-02-01").date:
        f = forecast_for_day(fc, d, cutoff)
        h = (f.startTime - f.publishTime).dt.total_seconds() / 3600
        flag = "" if len(f) == 24 else "  <-- INCOMPLETE"
        print(d, len(f), f"horizon {h.min():.1f}-{h.max():.1f}h", flag)