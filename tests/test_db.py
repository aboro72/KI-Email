from sqlalchemy import inspect

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
