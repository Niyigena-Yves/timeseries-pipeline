"""CRUD, time-series, and model endpoints for the crisis dataset."""

import os
from functools import lru_cache
from contextlib import asynccontextmanager
from typing import Any, Optional, Union

from fastapi import FastAPI, HTTPException, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field
from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError, PyMongoError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from src.database import (
    AnnualObservation,
    CrisisIndicators,
    create_tables,
    engine,
    SessionLocal,
    save_sql_record,
    sql_record_dict,
)
from src.predict import predict


class RecordPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cc3: Optional[str] = Field(default=None, min_length=3, max_length=3)
    country: str = Field(min_length=1, max_length=100)
    year: int = Field(ge=1800, le=2200)
    case: Optional[int] = None
    exch_usd: float
    gdp_weighted_default: float
    inflation_annual_cpi: float
    systemic_crisis: int = Field(ge=0, le=1)
    domestic_debt_in_default: int = Field(ge=0, le=1)
    sovereign_external_debt_default: int = Field(ge=0, le=1)
    independence: int = Field(ge=0, le=1)
    currency_crises: int = Field(ge=0, le=2)
    inflation_crises: int = Field(ge=0, le=1)
    banking_crisis: Union[int, str]


class PredictionRequest(BaseModel):
    records: list[dict[str, Any]]


@lru_cache(maxsize=1)
def get_mongo_collection() -> Collection:
    client = MongoClient(
        os.getenv("MONGO_URI", "mongodb://localhost:27017"),
        serverSelectionTimeoutMS=1500,
    )
    client.admin.command("ping")
    collection = client[os.getenv("MONGO_DATABASE", "african_crises")]["annual_records"]
    collection.create_index([("cc3", ASCENDING), ("year", ASCENDING)], unique=True)
    collection.create_index([("year", DESCENDING)])
    collection.create_index([("crisis.banking_crisis", ASCENDING), ("year", ASCENDING)])
    return collection


def normalize_target(value: Union[int, str]) -> int:
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"crisis", "1", "true"}:
            return 1
        if normalized in {"no_crisis", "no crisis", "0", "false"}:
            return 0
        raise ValueError("banking_crisis must be 0, 1, crisis, or no_crisis")
    if value not in (0, 1):
        raise ValueError("banking_crisis must be 0 or 1")
    return int(value)


def flat_payload(payload: RecordPayload) -> dict[str, Any]:
    record = payload.model_dump()
    record["banking_crisis"] = normalize_target(record["banking_crisis"])
    record["currency_crises"] = min(record["currency_crises"], 1)
    return record


def mongo_document(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "cc3": (record.get("cc3") or record["country"][:3]).upper(),
        "country": record["country"],
        "year": record["year"],
        "case": record.get("case"),
        "economic": {
            "exch_usd": record["exch_usd"],
            "gdp_weighted_default": record["gdp_weighted_default"],
            "inflation_annual_cpi": record["inflation_annual_cpi"],
        },
        "crisis": {
            key: record[key]
            for key in (
                "systemic_crisis",
                "domestic_debt_in_default",
                "sovereign_external_debt_default",
                "independence",
                "currency_crises",
                "inflation_crises",
                "banking_crisis",
            )
        },
    }


def mongo_flat(document: dict[str, Any]) -> dict[str, Any]:
    record = {key: value for key, value in document.items() if key not in {"_id", "economic", "crisis"}}
    record.update(document.get("economic", {}))
    record.update(document.get("crisis", {}))
    return record


def sql_query(
    session: Session,
    cc3: Optional[str] = None,
    start_year: Optional[int] = None,
    end_year: Optional[int] = None,
):
    statement = (
        select(AnnualObservation)
        .options(selectinload(AnnualObservation.country), selectinload(AnnualObservation.crisis))
        .join(AnnualObservation.country)
        .join(AnnualObservation.crisis)
    )
    if cc3:
        statement = statement.where(AnnualObservation.country_cc3 == cc3.upper())
    if start_year is not None:
        statement = statement.where(AnnualObservation.year >= start_year)
    if end_year is not None:
        statement = statement.where(AnnualObservation.year <= end_year)
    return session.scalars(statement.order_by(AnnualObservation.country_cc3, AnnualObservation.year)).all()


@asynccontextmanager
async def lifespan(_: FastAPI):
    create_tables(engine)
    yield


app = FastAPI(title="African Crisis Data API", version="1.0.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/sql/records", status_code=status.HTTP_201_CREATED)
def create_sql_record(payload: RecordPayload) -> dict[str, Any]:
    record = flat_payload(payload)
    session = SessionLocal()
    try:
        existing = session.scalar(
            select(AnnualObservation).where(
                AnnualObservation.country_cc3 == (record.get("cc3") or record["country"][:3]).upper(),
                AnnualObservation.year == record["year"],
            )
        )
        if existing:
            raise HTTPException(status_code=409, detail="Country-year record already exists")
        return save_sql_record(session, record)
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(status_code=409, detail="Country or country-year constraint failed") from error
    finally:
        session.close()


@app.get("/sql/records/latest")
def latest_sql_record(cc3: Optional[str] = None) -> dict[str, Any]:
    session = SessionLocal()
    try:
        records = sql_query(session, cc3=cc3)
        if not records:
            raise HTTPException(status_code=404, detail="No records found")
        return sql_record_dict(max(records, key=lambda row: row.year))
    finally:
        session.close()


@app.get("/sql/records")
def list_sql_records(
    cc3: Optional[str] = None,
    start_year: Optional[int] = Query(default=None, ge=1800, le=2200),
    end_year: Optional[int] = Query(default=None, ge=1800, le=2200),
) -> list[dict[str, Any]]:
    if start_year is not None and end_year is not None and start_year > end_year:
        raise HTTPException(status_code=422, detail="start_year must be <= end_year")
    session = SessionLocal()
    try:
        return [sql_record_dict(row) for row in sql_query(session, cc3, start_year, end_year)]
    finally:
        session.close()


@app.get("/sql/records/{cc3}/{year}")
def get_sql_record(cc3: str, year: int) -> dict[str, Any]:
    session = SessionLocal()
    try:
        rows = sql_query(session, cc3=cc3)
        record = next((row for row in rows if row.year == year), None)
        if record is None:
            raise HTTPException(status_code=404, detail="Record not found")
        return sql_record_dict(record)
    finally:
        session.close()


@app.put("/sql/records/{cc3}/{year}")
def update_sql_record(cc3: str, year: int, payload: RecordPayload) -> dict[str, Any]:
    record = flat_payload(payload)
    route_code = (record.get("cc3") or record["country"][:3]).upper()
    if route_code != cc3.upper() or record["year"] != year:
        raise HTTPException(status_code=422, detail="Payload country and year must match the URL")
    session = SessionLocal()
    try:
        existing = session.scalar(
            select(AnnualObservation).where(
                AnnualObservation.country_cc3 == cc3.upper(), AnnualObservation.year == year
            )
        )
        if existing is None:
            raise HTTPException(status_code=404, detail="Record not found")
        return save_sql_record(session, record)
    finally:
        session.close()


@app.delete("/sql/records/{cc3}/{year}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sql_record(cc3: str, year: int) -> Response:
    session = SessionLocal()
    try:
        record = session.scalar(
            select(AnnualObservation)
            .options(selectinload(AnnualObservation.crisis))
            .where(AnnualObservation.country_cc3 == cc3.upper(), AnnualObservation.year == year)
        )
        if record is None:
            raise HTTPException(status_code=404, detail="Record not found")
        session.delete(record)
        session.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    finally:
        session.close()


@app.post("/mongo/records", status_code=status.HTTP_201_CREATED)
def create_mongo_record(payload: RecordPayload) -> dict[str, Any]:
    document = mongo_document(flat_payload(payload))
    try:
        result = get_mongo_collection().insert_one(document)
        document["id"] = str(result.inserted_id)
        return mongo_flat(document)
    except DuplicateKeyError as error:
        raise HTTPException(status_code=409, detail="Country-year record already exists") from error
    except PyMongoError as error:
        raise HTTPException(status_code=503, detail="MongoDB is unavailable") from error


@app.get("/mongo/records/latest")
def latest_mongo_record(cc3: Optional[str] = None) -> dict[str, Any]:
    try:
        query = {"cc3": cc3.upper()} if cc3 else {}
        document = get_mongo_collection().find_one(query, sort=[("year", DESCENDING)])
        if document is None:
            raise HTTPException(status_code=404, detail="No records found")
        document["id"] = str(document.pop("_id"))
        return mongo_flat(document)
    except PyMongoError as error:
        raise HTTPException(status_code=503, detail="MongoDB is unavailable") from error


@app.get("/mongo/records")
def list_mongo_records(
    cc3: Optional[str] = None,
    start_year: Optional[int] = Query(default=None, ge=1800, le=2200),
    end_year: Optional[int] = Query(default=None, ge=1800, le=2200),
) -> list[dict[str, Any]]:
    if start_year is not None and end_year is not None and start_year > end_year:
        raise HTTPException(status_code=422, detail="start_year must be <= end_year")
    query: dict[str, Any] = {}
    if cc3:
        query["cc3"] = cc3.upper()
    year_filter: dict[str, int] = {}
    if start_year is not None:
        year_filter["$gte"] = start_year
    if end_year is not None:
        year_filter["$lte"] = end_year
    if year_filter:
        query["year"] = year_filter
    try:
        documents = get_mongo_collection().find(query).sort([("cc3", ASCENDING), ("year", ASCENDING)])
        return [mongo_flat(document) for document in documents]
    except PyMongoError as error:
        raise HTTPException(status_code=503, detail="MongoDB is unavailable") from error


@app.get("/mongo/records/{cc3}/{year}")
def get_mongo_record(cc3: str, year: int) -> dict[str, Any]:
    try:
        document = get_mongo_collection().find_one({"cc3": cc3.upper(), "year": year})
        if document is None:
            raise HTTPException(status_code=404, detail="Record not found")
        document["id"] = str(document.pop("_id"))
        return mongo_flat(document)
    except PyMongoError as error:
        raise HTTPException(status_code=503, detail="MongoDB is unavailable") from error


@app.put("/mongo/records/{cc3}/{year}")
def update_mongo_record(cc3: str, year: int, payload: RecordPayload) -> dict[str, Any]:
    record = flat_payload(payload)
    route_code = (record.get("cc3") or record["country"][:3]).upper()
    if route_code != cc3.upper() or record["year"] != year:
        raise HTTPException(status_code=422, detail="Payload country and year must match the URL")
    try:
        collection = get_mongo_collection()
        result = collection.replace_one({"cc3": cc3.upper(), "year": year}, mongo_document(record))
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Record not found")
        return mongo_flat(collection.find_one({"cc3": cc3.upper(), "year": year}))
    except PyMongoError as error:
        raise HTTPException(status_code=503, detail="MongoDB is unavailable") from error


@app.delete("/mongo/records/{cc3}/{year}", status_code=status.HTTP_204_NO_CONTENT)
def delete_mongo_record(cc3: str, year: int) -> Response:
    try:
        result = get_mongo_collection().delete_one({"cc3": cc3.upper(), "year": year})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Record not found")
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except PyMongoError as error:
        raise HTTPException(status_code=503, detail="MongoDB is unavailable") from error


@app.post("/predict")
def predict_endpoint(request: PredictionRequest) -> dict[str, list[Any]]:
    try:
        return {"predictions": predict(request.records)}
    except FileNotFoundError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
