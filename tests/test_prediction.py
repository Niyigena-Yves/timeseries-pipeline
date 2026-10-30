import joblib
import pandas as pd
from sklearn.dummy import DummyClassifier

from src.predict import predict
from src.preprocessing import FEATURES


def historical_record(year: int) -> dict:
    return {
        "cc3": "ZWE",
        "country": "Zimbabwe",
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
        "banking_crisis": int(year == 2023),
    }


def test_prediction_scores_latest_feature_complete_year(tmp_path):
    training = pd.DataFrame([[0.0] * len(FEATURES)], columns=FEATURES)
    model = DummyClassifier(strategy="constant", constant=1).fit(training, [1])
    model_path = tmp_path / "model.joblib"
    joblib.dump({"model": model, "features": FEATURES}, model_path)
    records = [historical_record(year) for year in range(2018, 2025)]

    result = predict(records, model_path)

    assert result == [
        {
            "cc3": "ZWE",
            "country": "Zimbabwe",
            "year": 2024,
            "prediction": 1,
            "label": "crisis",
            "probability": 1.0,
        }
    ]