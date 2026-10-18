"""PostgreSQL-backed API behavior tests."""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from app.main import app
from fastapi.testclient import TestClient


@pytest.fixture
def postgres_client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """Use the explicitly configured disposable PostgreSQL test database."""
    database_url = os.environ.get("TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip("TEST_DATABASE_URL is not configured")
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("TODO_DB_PATH", ":memory:")
    with TestClient(app) as client:
        yield client


def test_tc_032_postgres_task_round_trip(postgres_client: TestClient) -> None:
    """Create a task in Postgres and retrieve it through a new request."""
    create_response = postgres_client.post(
        "/api/v1/tasks",
        json={
            "title": "PostgreSQL 저장 확인",
            "assignees": ["팀원 A", "팀원 B"],
            "tags": ["cloud-e2e"],
        },
    )

    assert create_response.status_code == 201
    task = create_response.json()
    read_response = postgres_client.get(f"/api/v1/tasks/{task['id']}")

    assert read_response.status_code == 200
    assert read_response.json()["title"] == "PostgreSQL 저장 확인"
    assert read_response.json()["assignees"] == ["팀원 A", "팀원 B"]
    assert read_response.json()["tags"] == ["cloud-e2e"]
