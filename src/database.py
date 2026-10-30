"""Relational storage for country-year crisis observations."""

import os
from collections.abc import Iterator, Mapping
from typing import Any, Optional

from sqlalchemy import Float, ForeignKey, ForeignKeyConstraint, Integer, String, UniqueConstraint, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker


class Base(DeclarativeBase):
    pass


class Country(Base):
    __tablename__ = "countries"

    cc3: Mapped[str] = mapped_column(String(3), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    observations: Mapped[list["AnnualObservation"]] = relationship(back_populates="country")


class AnnualObservation(Base):
    __tablename__ = "annual_observations"
    __table_args__ = (UniqueConstraint("country_cc3", "year", name="uq_observation_country_year"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    country_cc3: Mapped[str] = mapped_column(ForeignKey("countries.cc3", ondelete="CASCADE"), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    case_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    exch_usd: Mapped[float] = mapped_column(Float, nullable=False)
    gdp_weighted_default: Mapped[float] = mapped_column(Float, nullable=False)
    inflation_annual_cpi: Mapped[float] = mapped_column(Float, nullable=False)
    country: Mapped[Country] = relationship(back_populates="observations")
    crisis: Mapped[Optional["CrisisIndicators"]] = relationship(
        back_populates="observation", cascade="all, delete-orphan", uselist=False
    )


class CrisisIndicators(Base):
    __tablename__ = "crisis_indicators"
    __table_args__ = (
        ForeignKeyConstraint(
            ["observation_id"], ["annual_observations.id"], ondelete="CASCADE"
        ),
        UniqueConstraint("observation_id", name="uq_crisis_observation"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    observation_id: Mapped[int] = mapped_column(Integer, nullable=False)
    systemic_crisis: Mapped[int] = mapped_column(Integer, nullable=False)
    domestic_debt_in_default: Mapped[int] = mapped_column(Integer, nullable=False)
    sovereign_external_debt_default: Mapped[int] = mapped_column(Integer, nullable=False)
    independence: Mapped[int] = mapped_column(Integer, nullable=False)
    currency_crises: Mapped[int] = mapped_column(Integer, nullable=False)
    inflation_crises: Mapped[int] = mapped_column(Integer, nullable=False)
    banking_crisis: Mapped[int] = mapped_column(Integer, nullable=False)
    observation: Mapped[AnnualObservation] = relationship(back_populates="crisis")


def make_engine(url: Optional[str] = None):
    database_url = url or os.getenv("DATABASE_URL", "sqlite:///./data/crises.db")
    options: dict[str, Any] = {"pool_pre_ping": True}
    if database_url.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False}
    return create_engine(database_url, **options)


engine = make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def create_tables(target_engine=engine) -> None:
    Base.metadata.create_all(target_engine)


def get_session() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def save_sql_record(session: Session, payload: Mapping[str, Any]) -> dict[str, Any]:
    country_code = str(payload.get("cc3") or payload["country"][:3].upper()).upper()
    country = session.get(Country, country_code)
    if country is None:
        country = Country(cc3=country_code, name=str(payload["country"]))
        session.add(country)
    elif country.name != payload["country"]:
        country.name = str(payload["country"])

    observation = session.scalar(
        select(AnnualObservation).where(
            AnnualObservation.country_cc3 == country_code,
            AnnualObservation.year == int(payload["year"]),
        )
    )
    if observation is None:
        observation = AnnualObservation(country_cc3=country_code, year=int(payload["year"]))
        session.add(observation)

    for field in ("case_number", "exch_usd", "gdp_weighted_default", "inflation_annual_cpi"):
        source_field = "case" if field == "case_number" else field
        setattr(observation, field, payload.get(source_field))

    session.flush()
    if observation.crisis is None:
        observation.crisis = CrisisIndicators(observation_id=observation.id)
    for field in (
        "systemic_crisis",
        "domestic_debt_in_default",
        "sovereign_external_debt_default",
        "independence",
        "currency_crises",
        "inflation_crises",
    ):
        setattr(observation.crisis, field, int(payload[field]))
    target = payload["banking_crisis"]
    observation.crisis.banking_crisis = int(target == "crisis") if isinstance(target, str) else int(target)
    session.commit()
    return sql_record_dict(observation)


def sql_record_dict(observation: AnnualObservation) -> dict[str, Any]:
    crisis = observation.crisis
    return {
        "cc3": observation.country.cc3,
        "country": observation.country.name,
        "year": observation.year,
        "case": observation.case_number,
        "exch_usd": observation.exch_usd,
        "gdp_weighted_default": observation.gdp_weighted_default,
        "inflation_annual_cpi": observation.inflation_annual_cpi,
        "systemic_crisis": crisis.systemic_crisis,
        "domestic_debt_in_default": crisis.domestic_debt_in_default,
        "sovereign_external_debt_default": crisis.sovereign_external_debt_default,
        "independence": crisis.independence,
        "currency_crises": crisis.currency_crises,
        "inflation_crises": crisis.inflation_crises,
        "banking_crisis": crisis.banking_crisis,
    }