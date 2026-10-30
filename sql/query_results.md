# Query Results

Results below were captured after importing `data/raw/african_crises.csv` into a temporary SQLite database using the SQLAlchemy schema and CSV seeder. The MySQL query forms are in `queries.sql`; the aggregations are portable to MySQL with the dialect-specific decade expression already shown there.

## 1. Dataset Totals

```sql
SELECT COUNT(*) AS observations, COUNT(DISTINCT country_cc3) AS countries,
       SUM(ci.banking_crisis) AS crisis_years
FROM annual_observations o
JOIN crisis_indicators ci ON ci.observation_id = o.id;
```

| observations | countries | crisis_years |
|---:|---:|---:|
| 1,059 | 13 | 94 |

## 2. Highest Country Crisis Rates

```sql
SELECT c.name, COUNT(*) AS observations, SUM(ci.banking_crisis) AS crisis_years,
       ROUND(AVG(ci.banking_crisis), 4) AS crisis_rate
FROM annual_observations o
JOIN countries c ON c.cc3 = o.country_cc3
JOIN crisis_indicators ci ON ci.observation_id = o.id
GROUP BY c.cc3, c.name
ORDER BY crisis_rate DESC
LIMIT 5;
```

| country | observations | crisis_years | crisis_rate |
|---|---:|---:|---:|
| Central African Republic | 58 | 19 | 0.3276 |
| Nigeria | 60 | 11 | 0.1833 |
| Zimbabwe | 90 | 15 | 0.1667 |
| Kenya | 67 | 8 | 0.1194 |
| Angola | 77 | 7 | 0.0909 |

## 3. Decades With the Highest Crisis Rates

```sql
SELECT FLOOR(o.year / 10) * 10 AS decade, COUNT(*) AS observations,
       SUM(ci.banking_crisis) AS crisis_years,
       ROUND(AVG(ci.banking_crisis), 4) AS crisis_rate
FROM annual_observations o
JOIN crisis_indicators ci ON ci.observation_id = o.id
GROUP BY FLOOR(o.year / 10)
ORDER BY crisis_rate DESC
LIMIT 5;
```

| decade | observations | crisis_years | crisis_rate |
|---:|---:|---:|---:|
| 1990 | 128 | 52 | 0.4063 |
| 1980 | 121 | 17 | 0.1405 |
| 2000 | 130 | 11 | 0.0846 |
| 2010 | 63 | 5 | 0.0794 |
| 1900 | 20 | 1 | 0.0500 |

## 4. Zimbabwe Date-Range Query

For `cc3='ZWE'` and `year BETWEEN 2000 AND 2010`, the inclusive range returns 11 observed rows, covering 2000 through 2010, with 10 banking-crisis years. No years are synthesized.

## MongoDB Result Cross-Check

The corresponding aggregation pipelines and `find` query are in `../mongo/design.md`. Their expected results for a complete import of the same CSV are: 13 latest-country documents; the same country and decade rates above; and 11 Zimbabwe documents in 2000–2010, of which 10 have `crisis.banking_crisis=1`. A MongoDB service was not reachable at `localhost:27017` during this implementation, so these Mongo outputs are cross-checked from the same source rows via SQL, not presented as a live MongoDB run.