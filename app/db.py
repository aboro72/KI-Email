from collections.abc import Generator

from sqlalchemy import create_engine, event, inspect, select
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
MONGO_BACKEND = settings.database_url.startswith(("mongodb://", "mongodb+srv://"))


class MongoStore:
    """MongoDB-Persistenz mit relationalem Arbeitsmodell für die bestehende Anwendung."""

    def __init__(self, uri: str):
        from pymongo import MongoClient

        self.client = MongoClient(uri, serverSelectionTimeoutMS=8000)
        self.database = self.client.get_default_database()

    def ping(self) -> None:
        self.client.admin.command("ping")

    def load_into_sqlite(self, connection) -> None:
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(table.delete())
        for table in Base.metadata.sorted_tables:
            documents = list(self.database[table.name].find({}, {"_id": 0}))
            if documents:
                columns = {column.name for column in table.columns}
                rows = [{key: value for key, value in document.items() if key in columns} for document in documents]
                for row in rows:
                    connection.execute(table.insert(), row)

    def snapshot(self, connection):
        return {table.name: {tuple(row[column.name] for column in table.primary_key): dict(row) for row in connection.execute(select(table)).mappings()} for table in Base.metadata.sorted_tables}

    def allocate_id(self, table):
        from pymongo import ReturnDocument
        latest = self.database[table.name].find_one(sort=[("id", -1)], projection={"id": 1})
        floor = int(latest.get("id", 0)) if latest else 0
        counters = self.database["_sequences"]
        counters.update_one({"_id": table.name}, {"$max": {"value": floor}}, upsert=True)
        return counters.find_one_and_update({"_id": table.name}, {"$inc": {"value": 1}}, return_document=ReturnDocument.AFTER)["value"]

    def export_from_sqlite(self, connection, baseline):
        """Nur eigene Änderungen schreiben, niemals fremde Datenbestände löschen."""
        from sqlalchemy.orm.exc import StaleDataError
        current = self.snapshot(connection)
        for table in Base.metadata.sorted_tables:
            collection = self.database[table.name]
            before, after = baseline.get(table.name, {}), current[table.name]
            for key in before.keys() - after.keys():
                collection.delete_one(dict(zip((column.name for column in table.primary_key), key)))
            for key, row in after.items():
                criteria = dict(zip((column.name for column in table.primary_key), key))
                if key not in before:
                    collection.insert_one({**row, "_id": row.get("id") or "|".join(str(value) for value in key)})
                else:
                    changed = {name: value for name, value in row.items() if value != before[key].get(name)}
                    if changed and collection.update_one(criteria, {"$set": changed}).matched_count == 0:
                        raise StaleDataError("Datensatz wurde zwischenzeitlich gelöscht")
        self.database["_metadata"].replace_one(
            {"_id": "aborodesk"},
            {"_id": "aborodesk", "backend": "mongodb", "schema_version": 1},
            upsert=True,
        )
        return current


mongo_store = MongoStore(settings.database_url) if MONGO_BACKEND else None

if MONGO_BACKEND:
    # SQLAlchemy bleibt nur ein gemeinsamer, nicht persistenter Arbeitsbereich.
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
else:
    connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
    engine = create_engine(settings.database_url, connect_args=connect_args)


class PersistenceSession(Session):
    def __init__(self, *args, **kwargs):
        self._mongo_engine = None
        if mongo_store is not None:
            # Jede Sitzung liest den aktuellen MongoDB-Stand in einen eigenen
            # Arbeitsbereich. Webapp und Worker teilen keine veraltete Kopie.
            self._mongo_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
            Base.metadata.create_all(self._mongo_engine)
            try:
                with self._mongo_engine.begin() as connection:
                    mongo_store.load_into_sqlite(connection)
                    self._baseline = mongo_store.snapshot(connection)
            except Exception:
                self._mongo_engine.dispose()
                raise
            kwargs["bind"] = self._mongo_engine
        super().__init__(*args, **kwargs)

    def commit(self):
        super().commit()
        if mongo_store is not None:
            self._baseline = mongo_store.export_from_sqlite(self.connection(), self._baseline)

    def close(self):
        try:
            super().close()
        finally:
            if self._mongo_engine is not None:
                self._mongo_engine.dispose()


@event.listens_for(PersistenceSession, "before_flush")
def reserve_mongo_ids(session, flush_context, instances):
    if mongo_store is None:
        return
    for item in session.new:
        table = inspect(item).mapper.local_table
        if len(table.primary_key.columns) == 1 and "id" in table.primary_key.columns and getattr(item, "id", None) is None:
            item.id = mongo_store.allocate_id(table)


SessionLocal = sessionmaker(bind=engine, class_=PersistenceSession, autoflush=False, autocommit=False)


def initialize_persistence() -> None:
    if mongo_store is None:
        return
    # Eigenständige Prozesse (Worker, CLI, Kandidatensuche) besitzen jeweils
    # ihre eigene In-Memory-SQLite-Arbeitsdatenbank. Sie muss vor dem Import
    # existieren; andernfalls scheitert der Import schon beim Leeren neuer
    # Tabellen wie ticket_comments.
    Base.metadata.create_all(engine)
    mongo_store.ping()
    with engine.begin() as connection:
        mongo_store.load_into_sqlite(connection)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
