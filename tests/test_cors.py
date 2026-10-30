"""CORS behavior tests for browser clients."""

from __future__ import annotations

import pytest
from app.main import app
from fastapi.testclient import TestClient

FRONTEND = "http://localhost:3000"


def test_preflight_from_frontend_is_allowed_without_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TTODO_API_TOKEN", "test-team-token")
    response = TestClient(app).options(
        "/api/v1/tasks",
        headers={
            "Origin": FRONTEND,
            "Access-Control-Request-Method": "PATCH",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == FRONTEND
    assert "PATCH" in response.headers["access-control-allow-methods"]


def test_unlisted_origin_is_rejected() -> None:
    response = TestClient(app).options(
        "/api/v1/tasks",
        headers={
            "Origin": "http://evil.example",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers
