# African Crises Time-Series Pipeline

This project analyzes annual banking and economic indicators for 13 African countries, stores country-year observations in MySQL and MongoDB, exposes CRUD/time-series APIs, and scores the latest feature-complete history with a trained classifier.

## Project Map

- `notebooks/01_eda_modeling.ipynb`: Task 1 EDA, lag and moving-average analysis, tuned model experiments, and model artifact export.
- `sql/schema.sql`, `sql/queries.sql`, `sql/erd.md`: normalized MySQL schema, sample queries, and ERD.
- `mongo/design.md`: document shape, indexes, sample record, and aggregation queries.
- `REPORT.md`: project report source; generate the PDF with `python scripts/build_report.py`.
- `src/database.py`: SQLAlchemy mappings and persistence helpers.
- `src/preprocessing.py`: shared cleaning and calendar-aware feature generation.
- `src/api/main.py`: SQL/Mongo CRUD, latest/range query, health, and prediction endpoints.
- `src/predict.py`: fetches API history and produces the latest model prediction.
- `src/seed.py`: imports the source CSV into one or both configured stores.

## Setup

```bash
cd timeseries-pipeline
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Set `DATABASE_URL` to a MySQL SQLAlchemy URL for MySQL, for example:

```text
mysql+pymysql://USER:PASSWORD@localhost:3306/african_crises
```

When unset, the API uses `sqlite:///./data/crises.db`, which is convenient for local development and tests. The MySQL DDL is in `sql/schema.sql`. MongoDB uses `MONGO_URI` (default `mongodb://localhost:27017`) and `MONGO_DATABASE` (default `african_crises`).

## Load the Data and Start the API

```bash
python -m src.seed --store sql
python -m src.seed --store mongo
python -m src.seed --store both
uvicorn src.api.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for the interactive API reference. SQL routes work with the configured relational database; Mongo routes require a reachable MongoDB instance and return `503` if it is unavailable.

## API Routes

Each backend has matching operations under `/sql/records` and `/mongo/records`:

| Method | Route | Purpose |
|---|---|---|
| `POST` | `/records` | Create one country-year record; duplicate keys return `409` |
| `GET` | `/records/{cc3}/{year}` | Read one record |
| `GET` | `/records/latest?cc3=ZWE` | Read the latest record, optionally for one country |
| `GET` | `/records?cc3=ZWE&start_year=2000&end_year=2010` | Read a country/date range; filters are optional |
| `PUT` | `/records/{cc3}/{year}` | Replace an existing record |
| `DELETE` | `/records/{cc3}/{year}` | Delete one record |

The API accepts the source dataset's flat column names. `banking_crisis` accepts `0`, `1`, `crisis`, or `no_crisis`; it is stored as `0`/`1`. A representative record is:

```json
{
  "cc3": "DZA",
  "country": "Algeria",
  "year": 1870,
  "case": 1,
  "exch_usd": 0.052264,
  "gdp_weighted_default": 0.0,
  "inflation_annual_cpi": 3.441455696,
  "systemic_crisis": 1,
  "domestic_debt_in_default": 0,
  "sovereign_external_debt_default": 0,
  "independence": 0,
  "currency_crises": 0,
  "inflation_crises": 0,
  "banking_crisis": "crisis"
}
```

## Train and Predict

Run the notebook from the project root (or its own `notebooks` directory). It reads `data/raw/african_crises.csv` and writes `models/crisis_model.joblib`, `models/experiment_table.csv`, and `data/processed/crises_features.csv`. The API `/predict` endpoint accepts a list of historical records. The CLI fetches history from the API, preprocesses it, loads the saved model, and scores the latest feature-complete year:

```bash
python -m src.predict --store sql --country-code ZWE --start-year 1980
```

Use `--store mongo`, `--api-url`, `--end-year`, or `--model-path` to change the source or model location. At least four uninterrupted prior annual observations are needed for the lag/three-year moving-average feature set. The classifier estimates the banking-crisis label for the latest observed year; a future-year forecast requires future values for any contemporaneous input features.

## Tests

```bash
pytest -q
```

Tests use an in-memory SQLite database and synthetic annual rows. They do not require MySQL or MongoDB services.