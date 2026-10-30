USE african_crises;

-- 1. Latest observation for every country.
SELECT c.name AS country, o.year, o.exch_usd, o.inflation_annual_cpi,
       ci.banking_crisis
FROM annual_observations AS o
JOIN countries AS c ON c.cc3 = o.country_cc3
JOIN crisis_indicators AS ci ON ci.observation_id = o.id
JOIN (
    SELECT country_cc3, MAX(year) AS latest_year
    FROM annual_observations
    GROUP BY country_cc3
) AS latest ON latest.country_cc3 = o.country_cc3 AND latest.latest_year = o.year
ORDER BY c.name;

-- 2. Banking-crisis counts and rates by country.
SELECT c.name AS country, COUNT(*) AS observations,
       SUM(ci.banking_crisis) AS crisis_years,
       ROUND(AVG(ci.banking_crisis), 4) AS crisis_rate
FROM annual_observations AS o
JOIN countries AS c ON c.cc3 = o.country_cc3
JOIN crisis_indicators AS ci ON ci.observation_id = o.id
GROUP BY c.cc3, c.name
ORDER BY crisis_rate DESC;

-- 3. Crisis rate by decade.
SELECT FLOOR(o.year / 10) * 10 AS decade,
       COUNT(*) AS observations,
       SUM(ci.banking_crisis) AS crisis_years,
       ROUND(AVG(ci.banking_crisis), 4) AS crisis_rate
FROM annual_observations AS o
JOIN crisis_indicators AS ci ON ci.observation_id = o.id
GROUP BY FLOOR(o.year / 10)
ORDER BY decade;

-- 4. Country-year records in a requested range (replace parameters).
SELECT c.name AS country, o.year, o.exch_usd, o.inflation_annual_cpi,
       ci.banking_crisis
FROM annual_observations AS o
JOIN countries AS c ON c.cc3 = o.country_cc3
JOIN crisis_indicators AS ci ON ci.observation_id = o.id
WHERE c.cc3 = 'ZWE' AND o.year BETWEEN 2000 AND 2010
ORDER BY o.year;