"""Database connections and schema migrations for SQLite and PostgreSQL."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from importlib import import_module
from pathlib import Path
from typing import Protocol, cast
from urllib.parse import parse_qs, unquote, urlparse

from fastapi import HTTPException

from app.settings import get_setting, is_worker_request

ROOT = Path(__file__).resolve().parent.parent
SQLITE_MIGRATIONS = ROOT / "migrations"
POSTGRES_MIGRATIONS = ROOT / "migrations" / "postgres"


class Row(Protocol):
    """The indexed and named access shared by database result rows."""

    def __getitem__(self, key: str) -> object: ...


class Cursor(Protocol):
    """The result operations used by the API."""

    @property
    def lastrowid(self) -> int | None: ...

    def fetchone(self) -> Row | None: ...

    def fetchall(self) -> Sequence[Row]: ...


class DatabaseConnection(Protocol):
    """The database operations used by API handlers."""

    is_postgres: bool

    def execute(self, query: str, parameters: Sequence[object] = ()) -> Cursor: ...

    def executemany(
        self, query: str, parameters: Sequence[Sequence[object]]
    ) -> None: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...

    def close(self) -> None: ...


class PostgreSQLCursorProtocol(Protocol):
    """The subset of pg8000 cursor behavior used by the adapter."""

    description: Sequence[Sequence[object]] | None

    def execute(self, query: str, parameters: Sequence[object] = ()) -> None: ...

    def executemany(
        self, query: str, parameters: Sequence[Sequence[object]]
    ) -> None: ...

    def fetchone(self) -> Sequence[object] | None: ...

    def fetchall(self) -> Sequence[Sequence[object]]: ...

    def close(self) -> None: ...


class PostgreSQLDriver(Protocol):
    """The pg8000 DB-API connection factory used by the application."""

    def connect(
        self,
        *,
        user: str,
        password: str,
        host: str,
        port: int,
        database: str | None,
        ssl_context: bool,
    ) -> PostgreSQLConnectionProtocol: ...


class PostgreSQLConnectionProtocol(Protocol):
    """The subset of pg8000 connection behavior used by the adapter."""

    def cursor(self) -> PostgreSQLCursorProtocol: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...

    def close(self) -> None: ...


pg8000_dbapi = cast(PostgreSQLDriver, import_module("pg8000.dbapi"))


class SQLiteConnection:
    """Adapt a SQLite connection to the API database interface."""

    is_postgres = False

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def execute(self, query: str, parameters: Sequence[object] = ()) -> Cursor:
        return cast(Cursor, self._connection.execute(query, parameters))

    def executemany(self, query: str, parameters: Sequence[Sequence[object]]) -> None:
        self._connection.executemany(query, parameters)

    def commit(self) -> None:
        self._connection.commit()

    def rollback(self) -> None:
        self._connection.rollback()

    def close(self) -> None:
        self._connection.close()


class PostgreSQLConnection:
    """Adapt a PostgreSQL connection and its parameter syntax."""

    is_postgres = True

    def __init__(self, connection: PostgreSQLConnectionProtocol) -> None:
        self._connection = connection

    def execute(self, query: str, parameters: Sequence[object] = ()) -> Cursor:
        cursor = self._connection.cursor()
        cursor.execute(query.replace("?", "%s"), tuple(parameters))
        return PostgreSQLCursor(cursor)

    def executemany(self, query: str, parameters: Sequence[Sequence[object]]) -> None:
        cursor = self._connection.cursor()
        cursor.executemany(query.replace("?", "%s"), parameters)
        cursor.close()

    def commit(self) -> None:
        self._connection.commit()

    def rollback(self) -> None:
        self._connection.rollback()

    def close(self) -> None:
        self._connection.close()


class PostgreSQLCursor:
    """Expose PostgreSQL result rows as mappings."""

    def __init__(self, cursor: PostgreSQLCursorProtocol) -> None:
        self._cursor = cursor
        self._columns = [str(column[0]) for column in cursor.description or []]

    @property
    def lastrowid(self) -> None:
        return None

    def fetchone(self) -> dict[str, object] | None:
        row = self._cursor.fetchone()
        if row is None:
            return None
        return dict(zip(self._columns, row, strict=True))

    def fetchall(self) -> list[dict[str, object]]:
        return [
            dict(zip(self._columns, row, strict=True))
            for row in self._cursor.fetchall()
        ]


def _apply_sqlite_migrations(connection: sqlite3.Connection) -> None:
    """Apply pending SQLite migrations."""
    connection.execute("BEGIN IMMEDIATE")
    connection.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY)"
    )
    applied = {
        int(row[0])
        for row in connection.execute("SELECT version FROM schema_migrations")
    }
    for migration in sorted(SQLITE_MIGRATIONS.glob("*.sql")):
        version = int(migration.stem.split("_")[0])
        if version in applied:
            continue
        statement = ""
        for line in migration.read_text().splitlines(keepends=True):
            statement += line
            if sqlite3.complete_statement(statement):
                connection.execute(statement)
                statement = ""
        if statement.strip():
            raise sqlite3.OperationalError(
                f"Incomplete SQL statement in {migration.name}"
            )
        connection.execute(
            "INSERT INTO schema_migrations(version) VALUES (?)", (version,)
        )
    connection.commit()


def _apply_postgres_migrations(
    connection: PostgreSQLConnectionProtocol,
) -> None:
    """Apply pending PostgreSQL migrations in a transaction."""
    adapter = PostgreSQLConnection(connection)
    try:
        adapter.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY)"
        )
        cursor = adapter.execute("SELECT version FROM schema_migrations")
        applied = {cast(int, row["version"]) for row in cursor.fetchall()}
        for migration in sorted(POSTGRES_MIGRATIONS.glob("*.sql")):
            version = int(migration.stem.split("_")[0])
            if version in applied:
                continue
            for statement in migration.read_text().split(";"):
                if statement.strip():
                    adapter.execute(statement)
            adapter.execute(
                "INSERT INTO schema_migrations(version) VALUES (?)", (version,)
            )
        connection.commit()
    except Exception:
        connection.rollback()
        raise


def connect_postgres(
    database_url: str, *, apply_migrations: bool = True
) -> DatabaseConnection:
    """Open an explicit PostgreSQL database, optionally applying app migrations."""
    parsed = urlparse(database_url)
    if not parsed.hostname or not parsed.username:
        raise ValueError("PostgreSQL URL must include a host and username.")
    ssl_mode = parse_qs(parsed.query).get("sslmode", [""])[0]
    postgres_connection = pg8000_dbapi.connect(
        user=unquote(parsed.username),
        password=unquote(parsed.password or ""),
        host=parsed.hostname,
        port=parsed.port or 5432,
        database=unquote(parsed.path.lstrip("/")) or None,
        ssl_context=ssl_mode in {"require", "verify-ca", "verify-full"},
    )
    try:
        if apply_migrations:
            _apply_postgres_migrations(postgres_connection)
    except Exception:
        postgres_connection.close()
        raise
    return PostgreSQLConnection(postgres_connection)


def connect() -> DatabaseConnection:
    """Open the configured database and apply its pending migrations."""
    database_url = get_setting("DATABASE_URL")
    if database_url:
        return connect_postgres(database_url, apply_migrations=not is_worker_request())
    if is_worker_request():
        raise HTTPException(
            status_code=503, detail="기본 Todo 데이터베이스가 설정되지 않았습니다."
        )

    raw_path = get_setting("TODO_DB_PATH") or str(ROOT / "data" / "todo.db")
    path = Path(raw_path)
    if raw_path != ":memory:":
        path.parent.mkdir(parents=True, exist_ok=True)
    sqlite_connection = sqlite3.connect(raw_path)
    sqlite_connection.row_factory = sqlite3.Row
    sqlite_connection.execute("PRAGMA foreign_keys = ON")
    try:
        _apply_sqlite_migrations(sqlite_connection)
    except Exception:
        sqlite_connection.rollback()
        sqlite_connection.close()
        raise
    return SQLiteConnection(sqlite_connection)


@contextmanager
def database() -> Iterator[DatabaseConnection]:
    """Yield one transactional connection and always close it."""
    connection = connect()
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
