# GB Wind Forecast: Day-Ahead Decision Portal

A web app for a UK energy buyer who must commit to day-ahead power purchases.
It shows (1) the wind forecast that was actually available at decision time and
(2) how accurate that forecast has been, quantified.

Live app:https://kjhwr-three.vercel.app/

## Scope and data
- National GB wind only, from Elexon BMRS: actuals from `FUELHH` (`fuelType=WIND`),
  forecasts from `WINDFOR`. No other data.
- Purchase decisions made in **January 2026**, so delivery days are **2 Jan to 1 Feb 2026**.

## Key assumptions (please read)
- **Decision time:** day-ahead purchases are decided on D-1. The brief gives no exact
  gate time, so I use **09:00 UK time on D-1** by default. It is configurable in the UI.
- **Forecast used for a delivery day:** for each target hour, the forecast with the
  **latest `publishTime` at or before the cutoff**. Forecasts are never averaged
  across publish times and never use information published after the cutoff.
- **Granularity:** `WINDFOR` is hourly, `FUELHH` is half-hourly. Accuracy metrics use the
  24 hourly timestamps per day, matching each forecast to the actual with the same
  `startTime`. The day chart shows all half-hourly actuals.
- **Time zone:** January has no daylight saving, so UK time equals UTC. Code converts
  via `Europe/London` so it would remain correct for other months.
- **Error sign:** `error = forecast - actual`. Positive means the forecast was too high.

## What the analysis shows (January 2026, 09:00 cutoff)
- 744 hourly comparisons. MAE ~2,022 MW (~17.9% of mean output), RMSE ~2,497 MW.
- The forecast was **above actual output in ~85% of hours**, by ~1,746 MW on average.
- Correlation between forecast and actual is ~0.93, so timing and shape are captured well;
  the issue is mainly a level offset plus ~1.4 GW of remaining error after removing the mean bias.
- Error grows with forecast horizon, but only modestly (MAE ~1.7 GW at 0-6h to ~2.4 GW at 66-72h).
- The shaded band on the chart is the 10th-90th percentile of past signed error, applied to the
  forecast: where actual output has typically landed.
- This analysis cannot explain *why* the bias exists (for example a definitional or curtailment
  difference between the two series); it only measures it.

## Repository layout
```
.
├── api/index.py            # Vercel entrypoint (exposes the FastAPI app)
├── vercel.json             # Vercel build + routing config
├── requirements.txt        # Python runtime deps for Vercel
├── Dockerfile              # Single image: builds React, serves it from FastAPI
├── backend/
│   ├── app/
│   │   ├── main.py         # FastAPI routes
│   │   ├── logic.py        # Forecast selection + metrics (core logic)
│   │   └── data.py         # CSV loading
│   ├── data/               # actuals.csv, forecasts.csv (fetched once, committed)
│   ├── scripts/            # fetch_data.py, check_data.py, diagnose.py
│   ├── tests/              # pytest tests for the selection logic
│   └── requirements.txt
└── frontend/               # React (Vite) + Recharts dashboard
```

## API
- `GET /api/forecast?day=YYYY-MM-DD&cutoff=HH:MM`: forecast available at the cutoff, actuals, error band
- `GET /api/metrics?cutoff=HH:MM`: MAE, RMSE, bias, percentiles, error by hour
- `GET /api/daily-errors?cutoff=HH:MM`: mean error per delivery day
- `GET /api/horizon-errors`: error by forecast horizon
- `GET /docs`: interactive API docs

## Run locally
Data is already committed, so no API calls are needed.

**Backend** (Python 3.12):
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate   |  macOS/Linux: source .venv/bin/activate
pip install -r backend/requirements.txt
cd backend
uvicorn app.main:app --reload
python -m pytest
```
**Frontend** (separate terminal; Node 20+):
```bash
cd frontend
npm install
npm run dev     # http://localhost:5173 (proxies /api to :8000)
```
**Docker** (single container, app on http://localhost:8000):
```bash
docker build -t wind-portal .
docker run --rm -p 8000:8000 wind-portal
```
**Refresh the data** (optional): `python backend/scripts/fetch_data.py`

## Deployment
Deployed on Vercel: the React build is served statically and the FastAPI app runs as a
Python function (`api/index.py`). Docker is used for local/containerised runs; Vercel
builds from source rather than running the Dockerfile.

## Limitations and next steps
- The error band is computed over all of January, so for early days it uses information
  not yet available at decision time. A production version would use a trailing window.
- One month of data: results describe January 2026 and should not be generalised.
- No bias-corrected forecast is offered, because that would be in-sample.

## AI tools disclosure
I used Claude (Anthropic) as an AI assistant for planning, code drafting, debugging and
README drafting. I reviewed, ran and tested the code, and I verified the results against
the raw Elexon data.
