# African Crises Time-Series Project Report

## Project Overview

This project uses the African Economic, Banking and Systemic Crises dataset: 1,059 annual country-year observations for 13 African countries spanning 1860-2014. The prediction target is `banking_crisis`, encoded as 1 for a crisis and 0 otherwise. The source has no null-valued cells, but it does have gaps in some countries' year sequences. We preserve those gaps and do not interpolate synthetic observations.

## Task 1: Preprocessing, EDA, and Modeling

The EDA examines temporal coverage, per-country year gaps, numeric distributions, target balance, crisis rates by decade and country, and relationships among crisis indicators. Exchange rates and inflation are skewed; inflation is transformed with a signed `log1p`, retaining Zimbabwe's genuine 2008 hyperinflation observation. Currency-crisis values are capped at 1 because four source rows use value 2. Missing calendar years are not filled. Calendar-aware lags and past-only three-year means are calculated within each country, and incomplete-history rows are excluded.

Six analytical questions are answered with visualizations in the notebook: long-run inflation/exchange-rate patterns; banking-crisis frequency by decade; current and lagged economic associations; past three-year averages by crisis status; co-occurrence of crisis types; and country/independence differences. Key computed results include: 8.88% of all observations are banking-crisis years; the 1990s have the largest decade rate (52/128, 40.63%); the Central African Republic has the largest country rate (19/58, 32.76%); prior-year crisis correlation is 0.7583; and mean signed-log past inflation MA3 is 2.9203 for crisis years versus 1.5821 for non-crisis years. These are descriptive associations, not causal estimates.

Three class-weighted tuned experiments are compared using precision, recall, F1, PR-AUC, and ROC-AUC. The train/test split is chronological (through 2000 for training, 2001-2014 for testing). Expanding validation windows are 1976-1980, 1981-1990, and 1991-2000; years are kept intact across countries. Earlier windows are excluded because they contain no positive training labels. Exp1 logistic regression and Exp2 random forest retain contemporaneous crisis indicators as upper-bound comparisons. Exp3, selected for deployment, removes current-year crisis/default flags and prior banking-crisis status.

| Experiment | Precision | Recall | F1 | PR-AUC | ROC-AUC |
|---|---:|---:|---:|---:|---:|
| Logistic regression, comparison | 0.833 | 1.000 | 0.909 | 0.996 | 1.000 |
| Random forest, comparison | 1.000 | 0.933 | 0.966 | 1.000 | 1.000 |
| Random forest, no current/lagged crisis indicators | 0.255 | 0.867 | 0.394 | 0.660 | 0.937 |

Exp3 is recall-oriented and produces false positives, so its decision threshold should reflect operational costs. The notebook saves `models/crisis_model.joblib` and `models/experiment_table.csv`.

## Task 2: Relational and Document Databases

The SQL design has three tables. `countries` stores country metadata; `annual_observations` stores year and economic measurements with a unique `(country_cc3, year)` constraint; `crisis_indicators` stores the crisis flags in a one-to-one relationship with each observation. Foreign keys cascade deletes. The ERD, MySQL DDL, and sample SELECT queries are in `sql/erd.md`, `sql/schema.sql`, and `sql/queries.sql`.

MongoDB stores one document per country-year in `annual_records`, embedding economic measurements and crisis flags to support the common read/write unit. A unique `(cc3, year)` index protects identity; additional indexes support year and crisis lookups. The sample document and four aggregation/range pipelines are documented in `mongo/design.md`.

The source CSV was imported through the SQLAlchemy implementation into SQLite for reproducible local verification. Query results are recorded in `sql/query_results.md`: 1,059 observations, 13 countries, and 94 crisis years; top country and decade rates are included there. The Zimbabwe 2000-2010 range returns 11 available rows and 10 crisis years. MySQL DDL is supplied, but a MySQL server was not available for a live engine test. MongoDB was not reachable at `localhost:27017`; the Mongo query values are cross-checked from the same source records and explicitly are not represented as native live Mongo execution output.

## Task 3: CRUD and Time-Series API

`src/api/main.py` exposes POST, GET-by-key, GET-latest, GET-by-date-range, PUT, and DELETE routes under both `/sql/records` and `/mongo/records`. The SQL backend defaults to SQLite for local development and accepts a MySQL `DATABASE_URL`; MongoDB is configured with `MONGO_URI` and `MONGO_DATABASE`. Validation rejects invalid years, malformed flags, duplicate country-years, and URL/body identity mismatches. Missing records return 404, duplicates return 409, and unavailable MongoDB returns 503. OpenAPI documentation is available at `/docs` when the service is running.

## Task 4: Prediction Script

`src/predict.py` fetches country history from either backend through the API, uses the shared calendar-aware preprocessing in `src/preprocessing.py`, loads the selected joblib artifact, and scores the latest feature-complete year. This is a current-year classification based on that year's observed covariates, not an unconditional future forecast; a future-year forecast would require future input values. The SQL-backed end-to-end smoke test retrieved Zimbabwe data through the API and scored 2013 as `crisis` with probability 0.644.

## Verification

The automated test suite passes five tests covering SQL round-trip/update/delete cascade, SQL API CRUD and time-series reads, calendar gaps and lag features, insufficient history, and model artifact scoring. The development database seeder imported all 1,059 source rows. Live MySQL and MongoDB service verification remains an environment prerequisite.

## Repository

Project code and documentation: [timeseries-pipeline](https://github.com/Niyigena-Yves/timeseries-pipeline)