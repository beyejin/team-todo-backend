"""API behavior tests mapped to documented TC-001 through TC-036."""

from __future__ import annotations

from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from types import SimpleNamespace
from typing import cast

import pytest
from app.db import database
from app.main import app
from fastapi.testclient import TestClient
from starlette.types import ASGIApp, Receive, Scope, Send


class WorkerEnvironment:
    """Inject Worker bindings through the ASGI request scope."""

    def __init__(
        self,
        application: ASGIApp,
        environment: object,
        barrier: Barrier | None = None,
    ) -> None:
        self.application = application
        self.environment = environment
        self.barrier = barrier

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        cast(dict[str, object], scope)["env"] = self.environment
        if self.barrier is not None:
            self.barrier.wait(timeout=5)
        await self.application(scope, receive, send)


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """Use a fresh SQLite file for every test."""
    monkeypatch.setenv("TODO_DB_PATH", str(tmp_path / "todo.db"))
    with TestClient(app) as test_client:
        yield test_client


def create(client: TestClient, **body: object) -> dict[str, object]:
    """Create a task and return its JSON representation."""
    response = client.post("/api/v1/tasks", json={"title": "작업", **body})
    assert response.status_code == 201
    return response.json()


def test_tc_001_tc_002_tc_003_create_defaults_normalization_and_utc(
    client: TestClient,
) -> None:
    task = create(client)
    assert task["status"] == "assigned"
    assert task["priority"] == "medium"
    assert task["assignees"] == task["tags"] == task["labels"] == []
    detailed = create(
        client,
        title="API 구현",
        description="Task CRUD",
        status="in_progress",
        priority="high",
        due_at="2026-10-20T09:00:00+09:00",
        assignees=[" 민수 ", "민수", "지윤"],
        tags=["backend", " sprint "],
        labels=["이번 주"],
    )
    assert detailed["due_at"] == "2026-10-20T00:00:00Z"
    assert detailed["assignees"] == ["민수", "지윤"]
    assert detailed["tags"] == ["backend", "sprint"]
    duplicate = create(client, assignees=[" 민수 ", "민수"], tags=[" api ", "api"])
    assert duplicate["assignees"] == ["민수"]
    assert duplicate["tags"] == ["api"]


def test_tc_033_api_token_protects_team_routes(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Configured shared servers reject missing and wrong bearer tokens."""
    monkeypatch.setenv("TTODO_API_TOKEN", "test-team-token")

    assert client.get("/api/v1/tasks").status_code == 401
    assert (
        client.get(
            "/api/v1/tasks", headers={"Authorization": "Bearer wrong-token"}
        ).status_code
        == 401
    )
    authorized = client.get(
        "/api/v1/tasks", headers={"Authorization": "Bearer test-team-token"}
    )
    assert authorized.status_code == 200


def test_tc_035_worker_token_is_required_and_validated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Worker token bindings fail closed and reject wrong bearer tokens."""
    monkeypatch.setenv("TTODO_API_TOKEN", "local-only-token")
    worker_app = WorkerEnvironment(app, SimpleNamespace())
    with TestClient(worker_app) as client:
        missing = client.get("/api/v1/tasks")
        assert missing.status_code == 503

    worker_app = WorkerEnvironment(app, SimpleNamespace(TTODO_API_TOKEN="worker-token"))
    with TestClient(worker_app) as client:
        missing_bearer = client.get("/api/v1/tasks")
        wrong = client.get(
            "/api/v1/tasks", headers={"Authorization": "Bearer wrong-token"}
        )
        assert missing_bearer.status_code == 401
        assert wrong.status_code == 401


def test_tc_035_worker_bindings_are_isolated_between_requests() -> None:
    """Concurrent Worker requests use the token from their own ASGI scopes."""
    barrier = Barrier(2)

    def request_status(environment: object, token: str) -> int:
        worker_app = WorkerEnvironment(app, environment, barrier)
        with TestClient(worker_app) as client:
            response = client.get(
                "/api/v1/tasks", headers={"Authorization": f"Bearer {token}"}
            )
        return response.status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(
            request_status,
            SimpleNamespace(TTODO_API_TOKEN="first-token"),
            "first-token",
        )
        second = executor.submit(
            request_status,
            SimpleNamespace(TTODO_API_TOKEN="second-token"),
            "first-token",
        )

    assert first.result() == 503
    assert second.result() == 401


def test_tc_036_worker_without_database_does_not_fall_back_to_sqlite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An authorized Worker request returns 503 when PostgreSQL is unset."""
    monkeypatch.setenv("DATABASE_URL", "")
    database_path = tmp_path / "todo.db"
    monkeypatch.setenv("TODO_DB_PATH", str(database_path))
    worker_app = WorkerEnvironment(app, SimpleNamespace(TTODO_API_TOKEN="worker-token"))
    with TestClient(worker_app) as client:
        response = client.get(
            "/api/v1/tasks", headers={"Authorization": "Bearer worker-token"}
        )

    assert response.status_code == 503
    assert not database_path.exists()


@pytest.mark.parametrize(
    "body",
    [
        {"description": "제목 없음"},
        {"title": "   "},
        {"title": "잘못된 값", "status": "blocked"},
        {"title": "잘못된 값", "priority": "urgent"},
        {"title": "날짜 오류", "due_at": "다음 주"},
    ],
)
def test_tc_004_tc_005_tc_006_invalid_create_is_rejected(
    client: TestClient, body: dict[str, object]
) -> None:
    response = client.post("/api/v1/tasks", json=body)
    assert response.status_code == 422
    assert "detail" in response.json()
    assert client.get("/api/v1/tasks").json()["total"] == 0


def test_tc_007_tc_008_tc_009_tc_010_tc_011_tc_012_list_filters_and_paging(
    client: TestClient,
) -> None:
    first = create(
        client,
        status="in_progress",
        priority="high",
        due_at="2026-10-20T09:00:00+09:00",
        assignees=["민수"],
        tags=["backend"],
        labels=["이번 주"],
    )
    second = create(client, status="assigned")
    create(client, status="completed")
    page = client.get("/api/v1/tasks?limit=2&offset=1").json()
    assert (page["limit"], page["offset"], page["total"]) == (2, 1, 3)
    assert page["items"][0]["id"] == second["id"]
    assert (
        client.get("/api/v1/tasks?status=assigned&status=in_progress").json()["total"]
        == 2
    )
    filtered = client.get(
        "/api/v1/tasks",
        params={
            "assignee": "민수",
            "priority": "high",
            "tag": "backend",
            "label": "이번 주",
        },
    ).json()
    assert [item["id"] for item in filtered["items"]] == [first["id"]]
    due = client.get(
        "/api/v1/tasks?due_from=2026-10-01T00:00:00Z&due_to=2026-10-31T23:59:59Z"
    ).json()
    assert [item["id"] for item in due["items"]] == [first["id"]]
    assert client.get("/api/v1/tasks?include_completed=false").json()["total"] == 2
    assert client.get("/api/v1/tasks").json()["total"] == 3


@pytest.mark.parametrize(
    ("query", "status"),
    [("status=blocked", 400), ("priority=urgent", 400), ("limit=101", 422)],
)
def test_tc_013_tc_014_invalid_list_filters_are_rejected(
    client: TestClient, query: str, status: int
) -> None:
    response = client.get(f"/api/v1/tasks?{query}")
    assert response.status_code == status
    assert "detail" in response.json()


def test_tc_015_tc_016_read_detail_and_not_found(client: TestClient) -> None:
    task = create(client)
    assert client.get(f"/api/v1/tasks/{task['id']}").json()["id"] == task["id"]
    assert client.get("/api/v1/tasks/999999").status_code == 404


def test_tc_017_tc_018_tc_019_tc_020_tc_021_tc_022_patch_rules(
    client: TestClient,
) -> None:
    task = create(
        client,
        description="기존 설명",
        due_at="2026-10-20T09:00:00+09:00",
        assignees=["민수"],
        tags=["backend"],
        labels=["중요"],
    )
    task_id = task["id"]
    response = client.patch(f"/api/v1/tasks/{task_id}", json={"title": "수정"})
    assert response.status_code == 200
    assert response.json()["title"] == "수정"
    assert response.json()["description"] == "기존 설명"
    replaced = client.patch(
        f"/api/v1/tasks/{task_id}", json={"assignees": ["지윤"], "tags": []}
    ).json()
    assert replaced["assignees"] == ["지윤"]
    assert replaced["tags"] == []
    assert replaced["labels"] == ["중요"]
    cleared = client.patch(
        f"/api/v1/tasks/{task_id}", json={"description": None, "due_at": None}
    ).json()
    assert cleared["description"] is cleared["due_at"] is None
    completed = client.patch(
        f"/api/v1/tasks/{task_id}", json={"status": "completed"}
    ).json()
    assert completed["status"] == "completed"
    assert (
        client.patch(f"/api/v1/tasks/{task_id}", json={"status": "blocked"}).status_code
        == 422
    )
    assert client.get(f"/api/v1/tasks/{task_id}").json()["status"] == "completed"
    assert (
        client.patch("/api/v1/tasks/999999", json={"title": "변경"}).status_code == 404
    )


def test_tc_023_to_tc_030_soft_delete_restore_and_errors(client: TestClient) -> None:
    task = create(client)
    task_id = task["id"]
    deleted = client.delete(f"/api/v1/tasks/{task_id}")
    assert deleted.status_code == 200
    assert deleted.json()["deleted_at"] is not None
    assert client.get("/api/v1/tasks").json()["total"] == 0
    assert client.get(f"/api/v1/tasks/{task_id}").status_code == 404
    assert (
        client.patch(f"/api/v1/tasks/{task_id}", json={"title": "x"}).status_code == 404
    )
    assert client.get("/api/v1/tasks/deleted").json()["total"] == 1
    assert client.delete(f"/api/v1/tasks/{task_id}").status_code == 404
    restored = client.post(f"/api/v1/tasks/{task_id}/restore")
    assert restored.status_code == 200
    assert restored.json()["deleted_at"] is None
    assert client.get(f"/api/v1/tasks/{task_id}").status_code == 200
    assert client.post(f"/api/v1/tasks/{task_id}/restore").status_code == 404
    assert client.delete("/api/v1/tasks/999999").status_code == 404
    assert client.post("/api/v1/tasks/999999/restore").status_code == 404


def test_tc_001_database_persistence_docs_and_openapi(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify stored tasks survive a new client session and docs are exposed."""
    task = create(client, title="지속성")
    monkeypatch.setenv("TODO_DB_PATH", str(tmp_path / "todo.db"))
    with TestClient(app) as restarted_client:
        assert (
            restarted_client.get(f"/api/v1/tasks/{task['id']}").json()["title"]
            == "지속성"
        )
    assert client.get("/docs").status_code == 200
    schema = client.get("/openapi.json").json()
    assert "/api/v1/tasks" in schema["paths"]


def test_tc_031_concurrent_first_connections_apply_migrations_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Serialize simultaneous first connections while applying migrations."""
    monkeypatch.setenv("TODO_DB_PATH", str(tmp_path / "concurrent.db"))
    barrier = Barrier(16)

    def inspect_schema(_: int) -> tuple[int, int]:
        barrier.wait()
        with database() as connection:
            task_tables = connection.execute(
                "SELECT count(*) FROM sqlite_master "
                "WHERE type = 'table' AND name IN "
                "('tasks', 'task_assignees', 'task_tags', 'task_labels')"
            ).fetchone()[0]
            migrations = connection.execute(
                "SELECT count(*) FROM schema_migrations"
            ).fetchone()[0]
            return task_tables, migrations

    with ThreadPoolExecutor(max_workers=16) as executor:
        results = list(executor.map(inspect_schema, range(16)))

    assert results == [(4, 1)] * 16
