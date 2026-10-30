from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from src.database import AnnualObservation, Base, CrisisIndicators, save_sql_record, sql_record_dict


def sample_record(crisis: str = "crisis") -> dict:
    return {
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
        "banking_crisis": crisis,
    }


def test_sql_record_round_trip_update_and_delete_cascade():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        created = save_sql_record(session, sample_record())
        assert created["banking_crisis"] == 1
        assert created["country"] == "Algeria"

        updated = save_sql_record(session, sample_record("no_crisis"))
        assert updated["banking_crisis"] == 0
        assert session.scalar(select(func.count()).select_from(AnnualObservation)) == 1

        observation = session.scalar(select(AnnualObservation))
        assert observation is not None
        assert sql_record_dict(observation)["year"] == 1870
        session.delete(observation)
        session.commit()
        assert session.scalar(select(func.count()).select_from(CrisisIndicators)) == 0

    Base.metadata.drop_all(engine)