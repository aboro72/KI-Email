#!/usr/bin/env python3
"""Copy the current SQLite database into MongoDB without modifying SQLite."""

from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone

from pymongo import MongoClient, ReplaceOne
from sqlalchemy import MetaData, create_engine, inspect, select, Table


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sqlite-url", default="sqlite:///./ki_email.db")
    parser.add_argument("--mongo-uri", default=os.environ.get("MIGRATION_MONGO_URI"), required=False)
    parser.add_argument("--replace", action="store_true", help="replace existing target collections")
    args = parser.parse_args()
    if not args.mongo_uri:
        raise SystemExit("Mongo URI über --mongo-uri oder MIGRATION_MONGO_URI angeben.")

    source_engine = create_engine(args.sqlite_url)
    source_metadata = MetaData()
    source_metadata.reflect(bind=source_engine)
    target_client = MongoClient(args.mongo_uri, serverSelectionTimeoutMS=10000)
    target_client.admin.command("ping")
    target_database = target_client.get_default_database()
    counts: dict[str, int] = {}

    with source_engine.connect() as connection:
        for table_name in inspect(source_engine).get_table_names():
            table = Table(table_name, source_metadata, autoload_with=source_engine)
            rows = connection.execute(select(table)).mappings().all()
            collection = target_database[table_name]
            if args.replace:
                collection.delete_many({})
            documents = []
            for row in rows:
                document = dict(row)
                document["_id"] = document.get("id") or "|".join(str(value) for value in document.values())
                documents.append(document)
            if documents:
                collection.bulk_write(
                    [
                        ReplaceOne({"_id": document["_id"]}, document, upsert=True)
                        for document in documents
                    ],
                    ordered=True,
                )
            counts[table_name] = len(documents)

    target_database["_metadata"].replace_one(
        {"_id": "aborodesk"},
        {
            "_id": "aborodesk",
            "backend": "mongodb",
            "source": "sqlite",
            "migrated_at": datetime.now(timezone.utc),
            "collections": counts,
        },
        upsert=True,
    )
    target_client.close()
    print("Migration erfolgreich:")
    for name, count in counts.items():
        print(f"  {name}: {count}")


if __name__ == "__main__":
    main()
