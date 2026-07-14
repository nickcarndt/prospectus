"""Postgres connection helpers for chunk storage and retrieval."""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from pgvector.psycopg import register_vector


def database_url() -> str:
    """Return DATABASE_URL or the local docker-compose default."""
    return os.getenv(
        "DATABASE_URL",
        "postgresql://prospectus:prospectus@localhost:5432/prospectus",
    )


@contextmanager
def connect() -> Iterator[psycopg.Connection]:
    """Open a Postgres connection with pgvector registered."""
    conn = psycopg.connect(database_url())
    register_vector(conn)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
