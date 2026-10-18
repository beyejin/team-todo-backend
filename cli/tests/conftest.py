"""Local HTTP test server for checking the public CLI contract."""

from __future__ import annotations

import json
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from typing import Any
from urllib.parse import parse_qs, urlsplit

import pytest


class StubApi(ThreadingHTTPServer):
    """Small local API that records the requests made by the CLI."""

    requests: list[dict[str, Any]]


@pytest.fixture
def api_server() -> Iterator[StubApi]:
    """Run a disposable HTTP API on an available local port."""

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self._respond()

        def do_POST(self) -> None:
            self._respond()

        def do_PATCH(self) -> None:
            self._respond()

        def do_DELETE(self) -> None:
            self._respond()

        def log_message(self, format: str, *args: object) -> None:
            return

        def _respond(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(length)
            body = json.loads(raw_body) if raw_body else None
            parsed_url = urlsplit(self.path)
            request = {
                "method": self.command,
                "path": parsed_url.path,
                "query": parse_qs(parsed_url.query),
                "body": body,
                "authorization": self.headers.get("Authorization"),
            }
            server = self.server
            assert isinstance(server, StubApi)
            server.requests.append(request)
            status, response = response_for(request)
            encoded = json.dumps(response).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

    server = StubApi(("127.0.0.1", 0), Handler)
    server.requests = []
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def response_for(request: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    """Return deterministic responses for the Todo API operations."""
    path = request["path"]
    method = request["method"]
    task_id = path.split("/")[4] if len(path.split("/")) > 4 else "1"
    query = request["query"]
    body = request["body"]
    if path == "/api/v1/kanban/tasks" and method == "POST":
        return 201, {
            "id": "00000000-0000-0000-0000-000000000099",
            "issue_number": 1,
            "title": body["title"],
            "description": body.get("description"),
            "status": body.get("status", "assigned"),
            "assignees": body.get("assignees", []),
            "labels": body.get("labels", []),
        }
    if path == "/api/v1/kanban/tasks" and method == "GET":
        return 200, {
            "items": [],
            "total": 0,
            "limit": int(query.get("limit", [20])[0]),
            "offset": int(query.get("offset", [0])[0]),
        }
    if path.startswith("/api/v1/kanban/tasks/") and method == "GET":
        return 200, {
            "id": path.rsplit("/", 1)[-1],
            "issue_number": 1,
            "title": "Review the demo",
            "status": "in_progress",
            "assignees": ["han-yejin"],
            "labels": ["Testing"],
        }
    if task_id == "404":
        return 404, {"detail": "Task not found."}
    if query.get("tag") == ["trigger-400"]:
        return 400, {"detail": "The date range is invalid."}
    if query.get("tag") == ["trigger-500"]:
        return 500, {"detail": "Unexpected server error."}
    if method == "POST" and path == "/api/v1/tasks":
        if isinstance(body, dict) and body.get("title") == "trigger-422":
            return 422, {
                "detail": [
                    {
                        "loc": ["body", "title"],
                        "msg": "Invalid title.",
                        "type": "value_error",
                    }
                ]
            }
        if not isinstance(body, dict) or not body.get("title"):
            return 422, {"detail": "A title is required."}
        return 201, {"id": 7, "status": "assigned", "priority": "medium", **body}
    if method == "GET" and path == "/api/v1/tasks":
        return 200, {
            "items": [
                {
                    "id": 7,
                    "title": "Send the report",
                    "status": "in_progress",
                    "priority": "high",
                }
            ],
            "total": 1,
            "limit": int(query.get("limit", [20])[0]),
            "offset": int(query.get("offset", [0])[0]),
        }
    if method == "GET" and path == "/api/v1/tasks/deleted":
        return 200, {"items": [], "total": 0, "limit": 20, "offset": 0}
    task = {
        "id": int(task_id),
        "title": "Send the report",
        "status": "assigned",
        "priority": "medium",
    }
    if method == "GET":
        return 200, task
    if method == "PATCH":
        if isinstance(body, dict) and body.get("title") == "trigger-422":
            return 422, {
                "detail": [
                    {
                        "loc": ["body", "title"],
                        "msg": "Invalid title.",
                        "type": "value_error",
                    }
                ]
            }
        return 200, {**task, **(body if isinstance(body, dict) else {})}
    if method == "DELETE":
        return 200, {**task, "deleted_at": "2026-10-13T00:00:00Z"}
    if method == "POST":
        return 200, {**task, "deleted_at": None}
    return 405, {"detail": "Method not allowed."}
