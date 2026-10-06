from sqlalchemy import create_engine, inspect, text
import pytest

import app.db as db_module


def test_mongo_initialization_creates_sqlite_working_tables(monkeypatch):
    class FakeMongoStore:
        loaded = False

        def ping(self):
            return None

        def load_into_sqlite(self, connection):
            self.loaded = True
            assert "ticket_comments" in inspect(connection).get_table_names()

    store = FakeMongoStore()
    monkeypatch.setattr(db_module, "mongo_store", store)

    db_module.initialize_persistence()

    assert store.loaded


def test_erp_upgrade_preserves_existing_data_and_is_repeatable():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE erp_documents (id INTEGER PRIMARY KEY, title TEXT NOT NULL)"))
        connection.execute(text("INSERT INTO erp_documents VALUES (1, 'Existing invoice')"))
        connection.execute(text("CREATE TABLE erp_payments (id INTEGER PRIMARY KEY, amount_cents INTEGER NOT NULL)"))
        connection.execute(text("INSERT INTO erp_payments VALUES (1, 1000)"))
    db_module.migrate_erp_schema(engine)
    db_module.migrate_erp_schema(engine)
    with engine.begin() as connection:
        row = connection.execute(text("SELECT title, overdue_notified_at, issued_pdf_base64 FROM erp_documents")).one()
        assert tuple(row) == ("Existing invoice", None, "")
        assert connection.execute(text("SELECT amount_cents, reverses_payment_id FROM erp_payments")).one() == (1000, None)
        connection.execute(text("INSERT INTO erp_payments VALUES (2, -1000, 1)"))
    from sqlalchemy.exc import IntegrityError
    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(text("INSERT INTO erp_payments VALUES (3, -1000, 1)"))
    engine.dispose()


def test_sqlite_initialization_runs_erp_upgrade(monkeypatch):
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE erp_documents (id INTEGER PRIMARY KEY)"))
    monkeypatch.setattr(db_module, "engine", engine)
    monkeypatch.setattr(db_module, "mongo_store", None)
    db_module.initialize_persistence()
    assert "overdue_notified_at" in {c["name"] for c in inspect(engine).get_columns("erp_documents")}
    engine.dispose()
