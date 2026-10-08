import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from prefstudio.api import create_app
from prefstudio.db import Base


@pytest.fixture
def db_url(tmp_path):
    # CI also runs the suite against PostgreSQL by setting TEST_DATABASE_URL.
    return os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{tmp_path / 'test.db'}"


@pytest.fixture
def app(db_url):
    app = create_app(db_url)
    yield app
    Base.metadata.drop_all(app.state.db.engine)
    app.state.db.engine.dispose()


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def session(app):
    with app.state.db.sessionmaker() as s:
        yield s
