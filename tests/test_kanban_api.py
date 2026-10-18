"""Shared Kanban board API behavior tests."""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import unquote, urlparse

import pytest
from app.db import pg8000_dbapi
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
        connection.commit()
    finally:
        connection.close()
    monkeypatch.setenv("KANBAN_DATABASE_URL", database_url)
    monkeypatch.setenv("KANBAN_BOARD_ID", BOARD_ID)
    monkeypatch.setenv("KANBAN_ACTOR_PROFILE_ID", ACTOR_ID)
    with TestClient(app) as client:
        yield client


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
