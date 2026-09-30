from collections.abc import Generator

from sqlalchemy import create_engine, select
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
                connection.execute(table.insert(), rows)

    def export_from_sqlite(self, connection) -> None:
        for table in Base.metadata.sorted_tables:
            rows = connection.execute(select(table)).mappings().all()
            collection = self.database[table.name]
            collection.delete_many({})
            if not rows:
                continue
            documents = []
            for row in rows:
                document = dict(row)
                document["_id"] = document.get("id") or "|".join(str(value) for value in document.values())
                documents.append(document)
            collection.insert_many(documents, ordered=True)
        self.database["_metadata"].replace_one(
            {"_id": "aborodesk"},
            {"_id": "aborodesk", "backend": "mongodb", "schema_version": 1},
            upsert=True,
        )


mongo_store = MongoStore(settings.database_url) if MONGO_BACKEND else None

if MONGO_BACKEND:
    # SQLAlchemy bleibt nur ein gemeinsamer, nicht persistenter Arbeitsbereich.
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
else:
    connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
    engine = create_engine(settings.database_url, connect_args=connect_args)


class PersistenceSession(Session):
    def commit(self):
        super().commit()
        if mongo_store is not None:
            mongo_store.export_from_sqlite(self.connection())


SessionLocal = sessionmaker(bind=engine, class_=PersistenceSession, autoflush=False, autocommit=False)


def initialize_persistence() -> None:
    if mongo_store is None:
        return
    mongo_store.ping()
    with engine.begin() as connection:
        mongo_store.load_into_sqlite(connection)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
