"""Database setup. SQLite by default; set DATABASE_URL for PostgreSQL."""

from __future__ import annotations

import os
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DEFAULT_URL = "sqlite:///./prefstudio.db"


class Base(DeclarativeBase):
    pass


def normalize_url(url: str) -> str:
    # Hosted Postgres often hands out postgres:// URLs; SQLAlchemy wants a driver name.
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


def make_engine(url: str | None = None):
    url = normalize_url(url or os.environ.get("DATABASE_URL", DEFAULT_URL))
    kwargs = {"connect_args": {"check_same_thread": False}} if url.startswith("sqlite") else {}
    return create_engine(url, **kwargs)


class Database:
    def __init__(self, url: str | None = None):
        self.engine = make_engine(url)
        self.sessionmaker = sessionmaker(self.engine, expire_on_commit=False)

    def create_all(self) -> None:
        from . import models  # noqa: F401  (registers the tables)

        Base.metadata.create_all(self.engine)

    def session(self) -> Iterator[Session]:
        with self.sessionmaker() as s:
            yield s
