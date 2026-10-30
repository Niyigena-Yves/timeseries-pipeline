from src.preprocessing import FEATURES, prepare_features


def record(year: int, country: str = "Example", crisis: int = 0) -> dict:
    return {
        "cc3": "EXM",
        "country": country,
        "year": year,
        "exch_usd": 1.0 + year / 1000,
        "gdp_weighted_default": 0.0,
        "inflation_annual_cpi": float(year % 10),
        "systemic_crisis": 0,
        "domestic_debt_in_default": 0,
        "sovereign_external_debt_default": 0,
        "independence": 1,
        "currency_crises": 0,
        "inflation_crises": 0,
        "banking_crisis": crisis,
    }


def test_calendar_gaps_are_not_bridged_and_features_use_prior_years():
    records = [record(year, crisis=int(year == 2022)) for year in (2018, 2019, 2021, 2022, 2023, 2024)]

    prepared = prepare_features(records)

    assert prepared.year.tolist() == [2024]
    row = prepared.iloc[0]
    assert set(FEATURES).issubset(prepared.columns)
    assert row["exch_usd_lag1"] == record(2023)["exch_usd"]
    assert row["exch_usd_lag2"] == record(2022)["exch_usd"]
    assert row["crisis_lag1"] == 0


def test_insufficient_history_has_no_model_ready_rows():
    assert prepare_features([record(2020), record(2021), record(2022)]).empty