# MongoDB Collection Design

## Collection: `annual_records`

Store one document per country-year. Embed the economic measurements and crisis flags because they are read and written together for API CRUD and time-series queries. Enforce uniqueness on `(cc3, year)` and index `(cc3, year)` for country history and range scans.

```javascript
db.annual_records.createIndex({ cc3: 1, year: 1 }, { unique: true });
db.annual_records.createIndex({ year: -1 });
db.annual_records.createIndex({ "crisis.banking_crisis": 1, year: 1 });
```

## Sample Document

```json
{
  "cc3": "DZA",
  "country": "Algeria",
  "year": 1870,
  "case": 1,
  "economic": {
    "exch_usd": 0.052264,
    "gdp_weighted_default": 0.0,
    "inflation_annual_cpi": 3.441455696
  },
  "crisis": {
    "systemic_crisis": 1,
    "domestic_debt_in_default": 0,
    "sovereign_external_debt_default": 0,
    "independence": 0,
    "currency_crises": 0,
    "inflation_crises": 0,
    "banking_crisis": 1
  }
}
```

`banking_crisis` is stored as integer `0`/`1` in both backends. API input also accepts the source strings `crisis` and `no_crisis`.

## Sample Queries and Result Interpretation

The following queries are intended for the imported CSV documents. The `find` results contain matching documents; aggregation results return the computed counts/rates.

```javascript
// 1. Latest observation for every country.
db.annual_records.aggregate([
  { $sort: { cc3: 1, year: -1 } },
  { $group: { _id: "$cc3", country: { $first: "$country" }, year: { $first: "$year" },
              banking_crisis: { $first: "$crisis.banking_crisis" } } },
  { $sort: { country: 1 } }
]);

// 2. Crisis count and rate per country.
db.annual_records.aggregate([
  { $group: { _id: "$country", observations: { $sum: 1 },
              crisis_years: { $sum: "$crisis.banking_crisis" },
              crisis_rate: { $avg: "$crisis.banking_crisis" } } },
  { $sort: { crisis_rate: -1 } }
]);

// 3. Date-range records for Zimbabwe (inclusive).
db.annual_records.find({ cc3: "ZWE", year: { $gte: 2000, $lte: 2010 } })
  .sort({ year: 1 });

// 4. Crisis rate by decade.
db.annual_records.aggregate([
  { $group: { _id: { $multiply: [{ $floor: { $divide: ["$year", 10] } }, 10] },
              observations: { $sum: 1 },
              crisis_years: { $sum: "$crisis.banking_crisis" },
              crisis_rate: { $avg: "$crisis.banking_crisis" } } },
  { $sort: { _id: 1 } }
]);
```

Expected results for a full import are 13 documents from the latest-per-country query; 13 country rows whose observation counts sum to 1,059 and crisis years sum to 94; and 11 Zimbabwe observations in 2000-2010 inclusive, with 10 crisis labels. The highest country rates are Central African Republic (19/58, 0.3276), Nigeria (11/60, 0.1833), and Zimbabwe (15/90, 0.1667). The highest decade rate is 1990 (52/128, 0.4063), followed by 1980 (17/121, 0.1405). These values were cross-checked against the same source records imported into SQLite. A live MongoDB service was unavailable at `localhost:27017` during implementation, so rerun these pipelines against MongoDB after starting the service to capture native execution output.