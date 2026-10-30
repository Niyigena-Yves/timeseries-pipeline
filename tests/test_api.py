from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import src.api.main as api


def payload(year: int = 1870, banking_crisis: str = "crisis") -> dict:
    return {
        "cc3": "DZA",
        "country": "Algeria",
        "year": year,
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
        "banking_crisis": banking_crisis,
    }


def test_sql_crud_and_time_series_routes(monkeypatch):
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    monkeypatch.setattr(api, "engine", test_engine)
    monkeypatch.setattr(api, "SessionLocal", sessionmaker(bind=test_engine, expire_on_commit=False))

    with TestClient(api.app) as client:
        created = client.post("/sql/records", json=payload())
        assert created.status_code == 201
        assert created.json()["banking_crisis"] == 1
        assert client.post("/sql/records", json=payload()).status_code == 409

        assert client.get("/sql/records/DZA/1870").json()["country"] == "Algeria"
        assert client.get("/sql/records", params={"cc3": "DZA", "start_year": 1870}).json()[0]["year"] == 1870
        assert client.get("/sql/records/latest", params={"cc3": "DZA"}).json()["year"] == 1870

        updated = client.put("/sql/records/DZA/1870", json=payload(banking_crisis="no_crisis"))
        assert updated.status_code == 200
        assert updated.json()["banking_crisis"] == 0

        assert client.delete("/sql/records/DZA/1870").status_code == 204
        assert client.get("/sql/records/DZA/1870").status_code == 404

    test_engine.dispose()