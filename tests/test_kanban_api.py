"""Shared Kanban board API behavior tests."""

from __future__ import annotations

import os
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from urllib.parse import unquote, urlparse

import pytest
from app import kanban
from app.db import DatabaseConnection, connect_postgres, pg8000_dbapi
from app.main import app
from fastapi.testclient import TestClient

ACTOR_ID = "00000000-0000-0000-0000-000000000001"
BOARD_ID = "00000000-0000-0000-0000-000000000004"
FIXTURE_SQL = Path(__file__).parent / "fixtures" / "kanban_schema.sql"


@pytest.fixture
def kanban_client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """Use only a disposable localhost PostgreSQL database for Kanban tests."""
    database_url = os.environ.get("TEST_KANBAN_DATABASE_URL")
    if database_url is None:
        pytest.skip("TEST_KANBAN_DATABASE_URL is not configured")
    parsed = urlparse(database_url)
    if parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        pytest.fail("TEST_KANBAN_DATABASE_URL must point to localhost")
    connection = pg8000_dbapi.connect(
        user=unquote(parsed.username or ""),
        password=unquote(parsed.password or ""),
        host=parsed.hostname,
        port=parsed.port or 5432,
        database=unquote(parsed.path.lstrip("/")) or None,
        ssl_context=False,
    )
    try:
        cursor = connection.cursor()
        cursor.execute("DROP SCHEMA public CASCADE")
        cursor.execute("CREATE SCHEMA public")
        for statement in FIXTURE_SQL.read_text().split(";"):
            if statement.strip():
                cursor.execute(statement)
        cursor.execute(
            "ALTER TABLE board_items ADD UNIQUE (board_id, issue_id), "
            "ADD UNIQUE (column_id, position)"
        )
        connection.commit()
    finally:
        connection.close()
    monkeypatch.setenv("KANBAN_DATABASE_URL", database_url)
    monkeypatch.setenv("KANBAN_BOARD_ID", BOARD_ID)
    monkeypatch.setenv("KANBAN_ACTOR_PROFILE_ID", ACTOR_ID)
    monkeypatch.delenv("TTODO_API_TOKEN", raising=False)
    with TestClient(app) as client:
        yield client


@pytest.fixture
def kanban_connection(kanban_client: TestClient) -> Iterator[DatabaseConnection]:
    """Inspect and arrange only the isolated database prepared by the API fixture."""
    connection = connect_postgres(
        os.environ["TEST_KANBAN_DATABASE_URL"], apply_migrations=False
    )
    try:
        yield connection
    finally:
        connection.close()


def test_tc_034_kanban_task_is_saved_to_board_and_read_back(
    kanban_client: TestClient,
) -> None:
    """Create a task in the selected board and read it through the API."""
    created = kanban_client.post(
        "/api/v1/kanban/tasks",
        json={
            "title": "CLI로 실제 칸반에 TODO 저장",
            "description": "과제 #7 공유 보드 연동 확인",
            "status": "assigned",
            "assignees": ["han-yejin"],
            "labels": ["Testing"],
        },
    )

    assert created.status_code == 201, created.text
    task = created.json()
    assert task["status"] == "assigned"
    assert task["assignees"] == ["han-yejin"]
    assert task["labels"] == ["Testing"]

    fetched = kanban_client.get(f"/api/v1/kanban/tasks/{task['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == task
    listed = kanban_client.get("/api/v1/kanban/tasks")
    assert listed.status_code == 200
    assert listed.json()["items"] == [task]
    assert listed.json()["total"] == 1


def test_tc_037_kanban_status_moves_preserve_content(
    kanban_client: TestClient,
) -> None:
    """TC-037: Move through any status order and read persisted fields back."""
    created = kanban_client.post(
        "/api/v1/kanban/tasks",
        json={
            "title": "상태 이동",
            "description": "내용 보존",
            "assignees": ["han-yejin"],
            "labels": ["Testing"],
        },
    )
    assert created.status_code == 201
    previous = created.json()
    path = f"/api/v1/kanban/tasks/{previous['id']}"
    for status in ("completed", "in_progress", "assigned"):
        response = kanban_client.patch(path, json={"status": status})
        assert response.status_code == 200, response.text
        updated = response.json()
        assert updated["status"] == status
        assert updated["column_id"] != previous["column_id"]
        assert updated["updated_at"] > previous["updated_at"]
        for field in (
            "id",
            "issue_number",
            "title",
            "description",
            "created_at",
            "board_id",
            "assignees",
            "labels",
        ):
            assert updated[field] == previous[field]
        assert kanban_client.get(path).json() == updated
        assert kanban_client.get("/api/v1/kanban/tasks").json()["items"] == [updated]
        previous = updated


def test_tc_038_same_status_keeps_order_and_timestamp(
    kanban_client: TestClient,
) -> None:
    """TC-038: Retrying the current status does not reorder or touch the issue."""
    first = kanban_client.post("/api/v1/kanban/tasks", json={"title": "첫 작업"}).json()
    second = kanban_client.post(
        "/api/v1/kanban/tasks", json={"title": "둘째 작업"}
    ).json()
    response = kanban_client.patch(
        f"/api/v1/kanban/tasks/{first['id']}", json={"status": "assigned"}
    )
    assert response.status_code == 200, response.text
    assert response.json() == first
    assert kanban_client.get("/api/v1/kanban/tasks").json()["items"] == [first, second]


def test_tc_039_move_appends_after_existing_target_tasks(
    kanban_client: TestClient,
) -> None:
    """TC-039: Move to the end of the target column without shifting other rows."""
    target = kanban_client.post(
        "/api/v1/kanban/tasks", json={"title": "기존 완료", "status": "completed"}
    ).json()
    moving = kanban_client.post("/api/v1/kanban/tasks", json={"title": "이동"}).json()
    response = kanban_client.patch(
        f"/api/v1/kanban/tasks/{moving['id']}", json={"status": "completed"}
    )
    assert response.status_code == 200, response.text
    assert response.json()["position"] == target["position"] + 1
    items = kanban_client.get("/api/v1/kanban/tasks").json()["items"]
    assert [item["id"] for item in items] == [target["id"], moving["id"]]
    assert items[0] == target


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"status": None},
        {"status": "done"},
        {"status": "completed", "title": "몰래 수정"},
    ],
)
def test_tc_040_status_patch_rejects_invalid_or_extra_fields(
    kanban_client: TestClient,
    payload: dict[str, object],
) -> None:
    """TC-040: A status-only PATCH rejects missing, null, unknown and extra input."""
    task = kanban_client.post("/api/v1/kanban/tasks", json={"title": "유지"}).json()
    path = f"/api/v1/kanban/tasks/{task['id']}"
    assert kanban_client.patch(path, json=payload).status_code == 422
    assert kanban_client.get(path).json() == task


def test_tc_041_status_patch_respects_board_and_membership(
    kanban_client: TestClient,
    kanban_connection: DatabaseConnection,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """TC-041: Other-board and missing issues are 404; a nonmember is 403."""
    other_board = "00000000-0000-0000-0000-000000000011"
    task = kanban_client.post(
        "/api/v1/kanban/tasks", json={"title": "현재 보드"}
    ).json()
    path = f"/api/v1/kanban/tasks/{task['id']}"
    kanban_connection.execute(
        "INSERT INTO boards(id, project_id, name, created_by) "
        "SELECT ?, project_id, '다른 보드', created_by FROM boards WHERE id = ?",
        (other_board, BOARD_ID),
    )
    kanban_connection.commit()
    monkeypatch.setenv("KANBAN_BOARD_ID", other_board)
    assert kanban_client.patch(path, json={"status": "completed"}).status_code == 404
    monkeypatch.setenv("KANBAN_BOARD_ID", BOARD_ID)
    assert kanban_client.get(path).json() == task
    assert (
        kanban_client.patch(
            "/api/v1/kanban/tasks/00000000-0000-0000-0000-000000000099",
            json={"status": "completed"},
        ).status_code
        == 404
    )
    monkeypatch.setenv(
        "KANBAN_ACTOR_PROFILE_ID", "00000000-0000-0000-0000-000000000099"
    )
    assert kanban_client.patch(path, json={"status": "completed"}).status_code == 403
    monkeypatch.setenv("KANBAN_ACTOR_PROFILE_ID", ACTOR_ID)
    assert kanban_client.get(path).json() == task


def test_tc_042_missing_target_column_leaves_task_unchanged(
    kanban_client: TestClient,
    kanban_connection: DatabaseConnection,
) -> None:
    """TC-042: Missing status columns fail with 409 without changing stored rows."""
    task = kanban_client.post("/api/v1/kanban/tasks", json={"title": "유지"}).json()
    kanban_connection.execute(
        "DELETE FROM board_columns WHERE id = '00000000-0000-0000-0000-000000000010'"
    )
    kanban_connection.commit()
    path = f"/api/v1/kanban/tasks/{task['id']}"
    assert kanban_client.patch(path, json={"status": "completed"}).status_code == 409
    assert kanban_client.get(path).json() == task


def test_tc_043_concurrent_creates_and_moves_have_unique_positions(
    kanban_client: TestClient,
) -> None:
    """TC-043: Concurrent creates and moves serialize the target append position."""
    moving = [
        kanban_client.post("/api/v1/kanban/tasks", json={"title": f"이동 {i}"}).json()
        for i in range(4)
    ]
    barrier = Barrier(8)

    def change(index: int) -> tuple[int, dict[str, object]]:
        barrier.wait(timeout=10)
        with TestClient(app) as client:
            if index < len(moving):
                response = client.patch(
                    f"/api/v1/kanban/tasks/{moving[index]['id']}",
                    json={"status": "completed"},
                )
            else:
                response = client.post(
                    "/api/v1/kanban/tasks",
                    json={"title": f"새 완료 {index}", "status": "completed"},
                )
        return response.status_code, response.json()

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(change, range(8)))
    assert [code for code, _ in results] == [200] * 4 + [201] * 4
    items = kanban_client.get("/api/v1/kanban/tasks").json()["items"]
    assert len(items) == 8
    assert all(item["status"] == "completed" for item in items)
    assert sorted(item["position"] for item in items) == list(range(8))


def test_tc_044_worker_column_grants_allow_only_status_movement(
    kanban_client: TestClient,
    kanban_connection: DatabaseConnection,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """TC-044: RLS grants allow status moves without title edits or deletions."""
    task = kanban_client.post(
        "/api/v1/kanban/tasks", json={"title": "권한 검증"}
    ).json()
    kanban_connection.execute(
        "DO $$ BEGIN "
        "IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'ttodo_worker') THEN "
        "CREATE ROLE ttodo_worker NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE "
        "NOREPLICATION NOBYPASSRLS NOINHERIT; END IF; END $$"
    )
    kanban_connection.commit()
    migrations = Path(__file__).parent.parent / "migrations" / "supabase"
    kanban_connection.execute((migrations / "001_worker_access.sql").read_text())
    before = kanban_connection.execute(
        "SELECT has_column_privilege('ttodo_worker', 'public.issues', "
        "'updated_at', 'UPDATE') AS allowed"
    ).fetchone()
    assert before is not None and before["allowed"] is False
    kanban_connection.commit()
    kanban_connection.execute((migrations / "002_worker_status_update.sql").read_text())
    permissions = kanban_connection.execute(
        "SELECT "
        "has_column_privilege('ttodo_worker', 'public.issues', 'updated_at', 'UPDATE') "
        "AS can_touch_issue, "
        "has_column_privilege('ttodo_worker', 'public.issues', 'title', 'UPDATE') "
        "AS can_edit_title, "
        "has_table_privilege('ttodo_worker', 'public.issues', 'DELETE') AS can_delete, "
        "(SELECT relrowsecurity FROM pg_class WHERE oid = 'issues'::regclass) "
        "AS issues_rls, "
        "(SELECT relrowsecurity FROM pg_class WHERE oid = 'board_items'::regclass) "
        "AS board_items_rls"
    ).fetchone()
    assert permissions is not None
    assert permissions["can_touch_issue"] is True
    assert permissions["can_edit_title"] is False
    assert permissions["can_delete"] is False
    assert permissions["issues_rls"] is True
    assert permissions["board_items_rls"] is True
    kanban_connection.commit()

    def worker_connection(
        database_url: str, *, apply_migrations: bool = True
    ) -> DatabaseConnection:
        connection = connect_postgres(database_url, apply_migrations=apply_migrations)
        connection.execute("SET ROLE ttodo_worker")
        return connection

    monkeypatch.setattr(kanban, "connect_postgres", worker_connection)
    path = f"/api/v1/kanban/tasks/{task['id']}"
    response = kanban_client.patch(path, json={"status": "completed"})
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "completed"
    assert response.json()["title"] == task["title"]
    assert kanban_client.get(path).json() == response.json()


def test_tc_042_late_database_failure_rolls_back_board_and_issue(
    kanban_client: TestClient, kanban_connection: DatabaseConnection
) -> None:
    """TC-042: Failure after moving a board row rolls back both rows atomically."""
    task = kanban_client.post("/api/v1/kanban/tasks", json={"title": "트랜잭션"}).json()
    original = kanban_connection.execute(
        "SELECT updated_at FROM board_items WHERE issue_id = ?", (task["id"],)
    ).fetchone()
    assert original is not None
    kanban_connection.execute(
        "CREATE FUNCTION fail_issue_update() RETURNS trigger LANGUAGE plpgsql AS "
        "$$ BEGIN RAISE EXCEPTION 'forced test rollback'; END $$"
    )
    kanban_connection.execute(
        "CREATE TRIGGER fail_issue_update BEFORE UPDATE ON issues "
        "FOR EACH ROW EXECUTE FUNCTION fail_issue_update()"
    )
    kanban_connection.commit()
    path = f"/api/v1/kanban/tasks/{task['id']}"
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.patch(path, json={"status": "completed"})
    assert response.status_code == 500
    assert "forced test rollback" not in response.text
    assert kanban_client.get(path).json() == task
    after = kanban_connection.execute(
        "SELECT updated_at FROM board_items WHERE issue_id = ?", (task["id"],)
    ).fetchone()
    assert after is not None and after["updated_at"] == original["updated_at"]
