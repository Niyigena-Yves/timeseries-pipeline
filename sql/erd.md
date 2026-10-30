# Relational ERD

```mermaid
erDiagram
    COUNTRIES ||--o{ ANNUAL_OBSERVATIONS : has
    ANNUAL_OBSERVATIONS ||--|| CRISIS_INDICATORS : describes

    COUNTRIES {
        char cc3 PK
        varchar name UK
    }
    ANNUAL_OBSERVATIONS {
        bigint id PK
        char country_cc3 FK
        smallint year
        int case_number
        double exch_usd
        double gdp_weighted_default
        double inflation_annual_cpi
        unique country_cc3_year
    }
    CRISIS_INDICATORS {
        bigint id PK
        bigint observation_id FK_UK
        tinyint systemic_crisis
        tinyint domestic_debt_in_default
        tinyint sovereign_external_debt_default
        tinyint independence
        tinyint currency_crises
        tinyint inflation_crises
        tinyint banking_crisis
    }
```

`countries` holds one row per country, `annual_observations` stores continuous economic measurements, and `crisis_indicators` stores the binary/categorical flags for that country-year. The unique country/year constraint prevents duplicate time points; the one-to-one indicator relation keeps the main measurements and crisis labels separately queryable.