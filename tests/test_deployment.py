"""Deployment behavior mapped to TC-045 through TC-047 in DEPLOYMENT.md."""

import os
from pathlib import Path
from urllib.parse import urlparse, urlunparse
from uuid import uuid4

import pytest
from app.db import connect_postgres
from app.main import app
from fastapi.testclient import TestClient


@pytest.mark.parametrize("path", ["/api/v1/tasks", "/api/v1/kanban/tasks"])
def test_tc_045_vercel_requires_configured_token(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, path: str
) -> None:
    """TC-045: A Vercel deployment without its shared token fails closed."""
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("TODO_DB_PATH", str(tmp_path / "todo.db"))
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("TTODO_API_TOKEN", raising=False)
    with TestClient(app) as client:
        response = client.get(path)
        assert response.status_code == 503
        assert response.json()["detail"] == "API 토큰이 설정되지 않았습니다."
        assert client.get("/openapi.json").status_code == 200


@pytest.mark.parametrize("authorization", ["", "Bearer incorrect"])
def test_tc_045_vercel_rejects_missing_or_wrong_token(
    monkeypatch: pytest.MonkeyPatch, authorization: str
) -> None:
    """TC-045: Vercel API requests must provide the configured bearer token."""
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("TTODO_API_TOKEN", "deployment-test-token")
    with TestClient(app) as client:
        response = client.get("/api/v1/tasks", headers={"Authorization": authorization})
    assert response.status_code == 401


def test_tc_046_vercel_without_database_never_creates_sqlite(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """TC-046: An authorized Vercel request cannot fall back to local storage."""
    database_path = tmp_path / "must-not-exist.db"
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("TTODO_API_TOKEN", "deployment-test-token")
    monkeypatch.setenv("TODO_DB_PATH", str(database_path))
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/tasks",
            headers={"Authorization": "Bearer deployment-test-token"},
        )
    assert response.status_code == 503
    assert not database_path.exists()


def test_tc_047_vercel_uses_restricted_postgres_without_ddl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """TC-047: Real API writes work with RLS and no schema-creation permission."""
    database_url = os.environ.get("TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip("TEST_DATABASE_URL is not configured")
    parsed = urlparse(database_url)
    if parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        pytest.fail("TEST_DATABASE_URL must point to localhost")
    suffix = uuid4().hex
    schema = f"deployment_{suffix}"
    role = f"deployment_role_{suffix}"
    admin = connect_postgres(database_url, apply_migrations=False)
    try:
        admin.execute(
            f"CREATE ROLE {role} LOGIN PASSWORD 'deployment-test-password' "
            "NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS"
        )
        admin.execute(f"CREATE SCHEMA {schema}")
        admin.execute(f"SET search_path TO {schema}, pg_catalog")
        migration = Path(__file__).parents[1] / "migrations/postgres/001_initial.sql"
        for statement in migration.read_text().split(";"):
            if statement.strip():
                admin.execute(statement)
        admin.execute(f"GRANT USAGE ON SCHEMA {schema} TO {role}")
        admin.execute(f"ALTER ROLE {role} SET search_path TO {schema}, pg_catalog")
        admin.execute(f"GRANT SELECT ON tasks TO {role}")
        admin.execute(
            "GRANT INSERT (title, description, status, priority, due_at, "
            f"created_at, updated_at) ON tasks TO {role}"
        )
        admin.execute(
            "GRANT UPDATE (title, description, status, priority, due_at, "
            f"updated_at, deleted_at) ON tasks TO {role}"
        )
        for table, field in [
            ("task_assignees", "assignee_name"),
            ("task_tags", "tag"),
            ("task_labels", "label"),
        ]:
            admin.execute(f"GRANT SELECT, DELETE ON {table} TO {role}")
            admin.execute(f"GRANT INSERT (task_id, {field}) ON {table} TO {role}")
        for table in ["tasks", "task_assignees", "task_tags", "task_labels"]:
            admin.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
            admin.execute(
                f"CREATE POLICY runtime_access ON {table} "
                f"TO {role} USING (true) WITH CHECK (true)"
            )
        admin.commit()

        host = f"[{parsed.hostname}]" if parsed.hostname == "::1" else parsed.hostname
        netloc = f"{role}:deployment-test-password@{host}:{parsed.port or 5432}"
        monkeypatch.setenv("DATABASE_URL", urlunparse(parsed._replace(netloc=netloc)))
        monkeypatch.setenv("VERCEL", "1")
        monkeypatch.setenv("TTODO_API_TOKEN", "deployment-test-token")
        with TestClient(
            app, headers={"Authorization": "Bearer deployment-test-token"}
        ) as client:
            response = client.post(
                "/api/v1/tasks",
                json={
                    "title": "제한 역할 배포 확인",
                    "assignees": ["담당자"],
                    "tags": ["배포"],
                    "labels": ["테스트"],
                },
            )
            assert response.status_code == 201
            task_url = f"/api/v1/tasks/{response.json()['id']}"
            assert client.get(task_url).json()["labels"] == ["테스트"]
            updated = client.patch(
                task_url, json={"status": "completed", "tags": ["완료"]}
            )
            assert updated.status_code == 200
            assert updated.json()["tags"] == ["완료"]
            assert client.delete(task_url).status_code == 200
            assert client.get(task_url).status_code == 404
            assert client.post(f"{task_url}/restore").status_code == 200
        row = admin.execute(
            "SELECT has_schema_privilege(?, ?, 'CREATE') AS can_create, "
            "to_regclass(?) AS migration_table, "
            "has_sequence_privilege(?, ?, 'USAGE') AS can_use_sequence",
            (
                role,
                schema,
                f"{schema}.schema_migrations",
                role,
                f"{schema}.tasks_id_seq",
            ),
        ).fetchone()
        assert row is not None
        assert row["can_create"] is False
        assert row["migration_table"] is None
        assert row["can_use_sequence"] is False
    finally:
        admin.rollback()
        admin.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
        admin.execute(f"DROP ROLE IF EXISTS {role}")
        admin.commit()
        admin.close()
