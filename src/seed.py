"""Import the source CSV into SQL, MongoDB, or both configured stores."""

import argparse
from pathlib import Path

import pandas as pd

from src.database import SessionLocal, create_tables, save_sql_record

DEFAULT_CSV = Path(__file__).resolve().parents[1] / "data" / "raw" / "african_crises.csv"


def seed_sql(frame: pd.DataFrame) -> int:
    create_tables()
    session = SessionLocal()
    try:
        for record in frame.to_dict(orient="records"):
            save_sql_record(session, record)
    finally:
        session.close()
    return len(frame)


def seed_mongo(frame: pd.DataFrame) -> int:
    from pymongo import ReplaceOne

    from src.api.main import get_mongo_collection, mongo_document, normalize_target

    collection = get_mongo_collection()
    operations = []
    for record in frame.to_dict(orient="records"):
        record["banking_crisis"] = normalize_target(record["banking_crisis"])
        record["currency_crises"] = min(int(record["currency_crises"]), 1)
        document = mongo_document(record)
        operations.append(
            ReplaceOne({"cc3": document["cc3"], "year": document["year"]}, document, upsert=True)
        )
    if operations:
        collection.bulk_write(operations, ordered=False)
    return len(operations)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--store", choices=("sql", "mongo", "both"), default="sql")
    args = parser.parse_args()
    frame = pd.read_csv(args.csv)
    frame = frame.sort_values(["country", "year"]).reset_index(drop=True)

    if args.store in ("sql", "both"):
        print(f"SQL records imported: {seed_sql(frame)}")
    if args.store in ("mongo", "both"):
        print(f"MongoDB records imported: {seed_mongo(frame)}")


if __name__ == "__main__":
    main()