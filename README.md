Wind Forecast Intelligence

A UK wind generation forecast intelligence dashboard designed to support day-ahead energy procurement decisions. The application displays national wind generation forecasts, compares forecasts against actual generation, and evaluates forecast accuracy for January 2026.

Live application: https://wind-forecast-intelligencee-ek1m.vercel.app/

Backend API: https://wind-forecast-intelligencee.onrender.com/

GitHub repository: https://github.com/esha-05/wind-forecast-intelligencee

1. Project Overview

The dashboard helps a UK energy procurement team understand:

The latest eligible national wind generation forecast available at a day-ahead decision cutoff.

Actual national wind generation for each delivery hour.

Forecast errors and accuracy metrics.

Daily forecast performance and forecast-versus-actual trends.

The application uses only Elexon BMRS datasets:

FUELHH: Actual half-hourly generation filtered to fuelType=WIND.

WINDFOR: Published national wind generation forecasts.

2. Architecture

Frontend: React, TypeScript, Vite, Recharts
Backend: Python, FastAPI, Pandas
Data source: Elexon BMRS API
Deployment: Vercel (frontend), Render (backend)
Containerisation: Docker and Docker Compose configuration

Data flow

React Dashboard → FastAPI → Data Store and Cache → Elexon BMRS API → Data Processing and Accuracy Metrics → Dashboard

The backend retrieves Elexon data, processes forecast and actual generation records, selects eligible forecasts, calculates accuracy metrics, and returns results to the frontend.

3. Data Methodology

Forecast selection

Delivery period: January 1–31, 2026.

Decision cutoff: 08:00 UTC on the day before delivery.

The cutoff is an explicit project assumption, not an official Elexon market rule.

Forecasts published after the cutoff are excluded.

For each delivery hour, the latest eligible publishTime is selected.

Forecasts are matched with actual generation using hourly delivery timestamps.

Actual generation processing

FUELHH provides half-hourly actual generation records.

The two half-hourly readings within each delivery hour are averaged to produce an hourly actual generation value. An hourly value is only created when both half-hourly readings are available.

No missing generation values are replaced with zero.

Forecast accuracy metrics

Forecast error is calculated as:

Error = Forecast - Actual

MAE: Mean Absolute Error.

RMSE: Root Mean Squared Error.

Bias: Average signed forecast error.

MAPE: Mean Absolute Percentage Error.

Coverage: Matched hourly intervals divided by expected hourly intervals.

Positive bias indicates forecast overestimation; negative bias indicates underestimation.

MAPE excludes intervals where the absolute actual generation is below 1 source unit. Metrics are calculated using matched intervals only.

4. January 2026 Results

The following are pooled monthly metrics calculated across all 744 matched hourly intervals.

Metric

January 2026

Expected hourly intervals

744

Matched hourly intervals

744

Coverage

100%

MAE

2,142.12

RMSE

2,611.70

Bias

+1,851.90

MAPE

22.38%

Positive errors

633

Negative errors

111

MAPE exclusions

0

Key observation: The positive monthly bias indicates that the selected forecasts generally overestimated actual wind generation during January 2026.

All metric values are expressed in the source generation units returned by Elexon.

5. Independent Data Validation

The deployed application was independently compared with records retrieved directly from the Elexon BMRS API.

FUELHH actual generation

Validation

Result

Expected half-hourly records

1,488

Retrieved records

1,488

Unique timestamps

1,488

Duplicate timestamps

0

Incomplete settlement days

0

Constructed hourly actuals

744

WINDFOR forecast selection

Validation

Result

Raw forecast records retrieved

28,616

Eligible delivery hours selected

744

Missing raw forecasts

0

Forecast value mismatches

0

Publication timestamp mismatches

0

Application-to-source comparison

Across all 744 January delivery hours:

Forecast values matched the independently selected latest eligible Elexon forecasts.

Actual values matched independently aggregated FUELHH readings.

Selected publication timestamps matched.

No missing forecast or actual records were found in the comparison.

All 31 deployed API requests succeeded.

These checks validate the returned January dataset and the application's selection and aggregation results against the retrieved Elexon records.

6. API Endpoints

Method

Endpoint

Purpose

GET

/api/health

Backend health check

GET

/api/forecast?date&cutoff

Forecast data

GET

/api/accuracy?date&cutoff

Daily accuracy results

GET

/api/accuracy/summary?start_date&end_date&cutoff

Summary results

POST

/api/refresh

Refresh cached source data

Invalid inputs return HTTP 422. Upstream data failures return HTTP 502.

The backend uses an in-memory cache with a configurable one-hour default TTL.

7. Project Structure

wind-forecast-app/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── clients/
│   │   ├── core/
│   │   └── services/
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   ├── Dockerfile
│   ├── index.html
│   └── package.json
├── docker-compose.yml
├── .env.example
└── README.md

8. Run Locally

Backend

cd backend

python -m venv .venv

# Windows Git Bash
source .venv/Scripts/activate

pip install -r requirements.txt

uvicorn app.main:app --reload --port 8001

Backend documentation:

http://127.0.0.1:8001/docs

Frontend

Open another terminal:

cd frontend

npm install

npm run dev

Frontend:

http://localhost:5173

For local development, configure frontend/.env.local:

VITE_API_URL=http://127.0.0.1:8001

Run backend tests

cd backend
pytest

Run frontend tests and build

cd frontend
npm test
npm run build

9. Deployment

Frontend – Vercel

Repository: GitHub project.

Root directory: frontend.

Framework: Vite.

Build command: npm run build.

Output directory: dist.

Environment variable:

VITE_API_URL=https://wind-forecast-intelligencee.onrender.com

Live URL:

https://wind-forecast-intelligencee-ek1m.vercel.app/

Backend – Render

Repository: GitHub project.

Root directory: backend.

Runtime: Python.

Build command: pip install -r requirements.txt.

Start command:

uvicorn app.main:app --host 0.0.0.0 --port $PORT

Health check:

https://wind-forecast-intelligencee.onrender.com/api/health

10. Known Limitations

The 08:00 UTC day-ahead cutoff is a project assumption and can be changed.

The dashboard evaluates published wind generation forecasts; it does not train a separate machine learning forecasting model.

Wind forecast accuracy alone cannot determine the utility's complete procurement requirement. Demand forecasts, other generation sources, interconnector flows, and market prices would also be required.

The application uses an in-memory cache, which is not shared across multiple backend instances.

The forecast and actual generation values are displayed in the source units returned by Elexon.

Historical January 2026 evaluation results should not be interpreted as a guarantee of future forecast performance.

11. AI Usage Disclosure

AI tools, including ChatGPT (OpenAI) and Claude (Anthropic), were used to assist with development, debugging, code review, documentation, and project explanations. The implementation and validation results were reviewed and tested against the application and Elexon API.
