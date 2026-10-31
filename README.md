# Wind Forecast Intelligence

Dashboard for a UK utility to see (a) the latest national wind forecast available at a day-ahead decision time and (b) how accurate it was, for delivery days in January 2026. Uses only Elexon **FUELHH** (actual, `fuelType=WIND`) and **WINDFOR** (forecast).

## Status (honest)
| Item | State |
|---|---|
| Backend pytest (7 tests, synthetic fixtures) | Passed in build sandbox |
| Frontend vitest (3 tests) and `npm run build` | Passed in build sandbox |
| **Live Elexon integration** | **NOT verified.** The sandbox could not reach Elexon. Endpoint paths, parameters and field names (`startTime`, `publishTime`, `generation`, `fuelType`) follow the public v1 stream API from memory. Run once against the live API and adjust `backend/app/clients/elexon.py` if needed. Units are not confirmed, so the UI shows values as reported. |
| Docker / Compose | Config written, **not run** |
| Vercel / backend deployment, live URL | **Not done** (see steps below) |

## Architecture
React/Vite/Recharts (`frontend/`) -> FastAPI (`backend/app/api`) -> `services/store.py` (in-memory TTL cache) -> `clients/elexon.py` (httpx, 7-day windows, retry/backoff on 429/5xx, 30s timeout) -> `services/processing.py` (pandas selection + metrics).

## Methodology
- Timestamps parsed to UTC (January = GMT). Grid is 48 x 30-min intervals per day (1,488 for the month).
- **Cutoff assumption (not an official Elexon/market rule):** `DEFAULT_CUTOFF=08:00` UTC on the day *before* delivery. Change via env var or the UI.
- Per interval: keep forecasts with `publishTime <= cutoff`, take the latest `publishTime`; later publications are never used. No eligible forecast -> `missing_forecast`.
- Null generation is never turned into 0; such rows are dropped and the interval is marked missing. Duplicates are removed.
- Error = forecast − actual (positive = overestimate). MAE, RMSE, bias use matched intervals only. MAPE excludes |actual| < 1 (source units) and reports the excluded count. Coverage = matched / expected.

## API
`GET /api/health`, `GET /api/forecast?date&cutoff`, `GET /api/accuracy?date&cutoff`, `GET /api/accuracy/summary?start_date&end_date&cutoff`, `POST /api/refresh` (re-fetches; cached 1h otherwise). Invalid input -> 422; Elexon failure -> 502. No fallback to fake data.

## Run
```bash
# backend
cd backend && python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
uvicorn app.main:app --reload          # :8000
pytest
# frontend
cd frontend && npm install && npm run dev   # :5173 (VITE_API_URL defaults to http://localhost:8000)
npm test
# docker
cp .env.example .env && docker compose up --build -d   # app :5173, API :8000
docker compose ps; docker compose logs -f; docker compose down
```
Env vars: see `.env.example` (`DEFAULT_CUTOFF`, `CORS_ORIGINS`, `CACHE_TTL_SECONDS`, `CHUNK_DAYS`, `HTTP_TIMEOUT_SECONDS`, `ELEXON_BASE_URL`, `VITE_API_URL`).

## Deployment (manual)
- Backend (Render/Railway/Heroku-compatible): root `backend/`, Docker or `uvicorn app.main:app --host 0.0.0.0 --port $PORT`, health check `/api/health`, set `CORS_ORIGINS=<vercel url>`.
- Frontend (Vercel): root `frontend/`, build `npm run build`, output `dist`, env `VITE_API_URL=<backend url>`.
- Live URL: _not deployed yet_.

## Known limitations
Cutoff is an assumption; live API unverified; whole-month data is fetched in memory on first request (slow cold start); no screenshots; Docker/deploy untested; WINDFOR horizon start (15 Dec 2025) is a guess to cover multi-day-ahead forecasts.

## AI disclosure
Generated with Claude (Anthropic). Review before submission.

## Demo script (10 min)
**Client (5):** problem and cutoff assumption (1) -> Overview: pick 15 Jan, change cutoff, show publishTime changing (1.5) -> Accuracy: forecast vs actual, error chart, KPIs, sign convention (1.5) -> how it informs purchasing, limitations (1).
**Technical (5):** architecture (1) -> Elexon client windowing/retries (1) -> `build_intervals` and metrics (1.5) -> tests + `docker compose up` (1) -> deployment and limitations (0.5).
Checklist: run live API first, confirm data loads, record screen+audio, upload and verify link manually.
