"""CLI-to-HTTP behavior tests for every Todo API operation."""

from __future__ import annotations

import json
from http.server import ThreadingHTTPServer
from types import SimpleNamespace
from typing import Any

import pytest
from typer.testing import CliRunner

import ttodo.cli as cli
from ttodo.cli import app

runner = CliRunner()


def _invoke(server: ThreadingHTTPServer, args: list[str]) -> Any:
    """Run a CLI command against the local stub API."""
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    return runner.invoke(app, ["--base-url", base_url, *args])


def test_create_sends_task_fields_to_create_endpoint(api_server: Any) -> None:
    """Create sends all supplied fields through the generated API operation."""
    result = _invoke(
        api_server,
        [
            "create",
            "--title",
            "Send the report",
            "--description",
            "By Friday",
            "--status",
            "in_progress",
            "--priority",
            "high",
            "--due-at",
            "2026-10-20T09:00:00+09:00",
            "--assignee",
            "Jin",
            "--assignee",
            "Min",
            "--tag",
            "work",
            "--label",
            "weekly",
        ],
    )

    assert result.exit_code == 0, result.output
    request = api_server.requests[0]
    assert (request["method"], request["path"]) == ("POST", "/api/v1/tasks")
    assert request["body"] == {
        "title": "Send the report",
        "description": "By Friday",
        "status": "in_progress",
        "priority": "high",
        "due_at": "2026-10-20T09:00:00+09:00",
        "assignees": ["Jin", "Min"],
        "tags": ["work"],
        "labels": ["weekly"],
    }


def test_cli_uses_configured_team_api_token(
    api_server: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Send the optional team bearer token without printing it."""
    monkeypatch.setenv("TTODO_API_TOKEN", "test-team-token")
    result = _invoke(api_server, ["list"])

    assert result.exit_code == 0, result.output
    assert api_server.requests[0]["authorization"] == "Bearer test-team-token"
    assert "test-team-token" not in result.stdout
    assert "test-team-token" not in result.stderr


def test_kanban_create_uses_shared_board_api(
    api_server: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Create sends a task to the existing Kanban board endpoint."""
    monkeypatch.setenv("TTODO_API_TOKEN", "test-team-token")
    result = _invoke(
        api_server,
        [
            "kanban",
            "create",
            "--title",
            "Review the demo",
            "--status",
            "in_progress",
            "--assignee",
            "han-yejin",
            "--label",
            "Testing",
        ],
    )

    assert result.exit_code == 0, result.output
    request = api_server.requests[0]
    assert (request["method"], request["path"]) == (
        "POST",
        "/api/v1/kanban/tasks",
    )
    assert request["body"] == {
        "title": "Review the demo",
        "status": "in_progress",
        "assignees": ["han-yejin"],
        "labels": ["Testing"],
    }
    assert request["authorization"] == "Bearer test-team-token"
    assert "#1 Review the demo" in result.stdout


def test_kanban_list_uses_shared_board_api(api_server: Any) -> None:
    """List uses the dedicated shared board endpoint and its pagination."""
    result = _invoke(api_server, ["kanban", "list", "--limit", "5", "--offset", "2"])

    assert result.exit_code == 0, result.output
    request = api_server.requests[0]
    assert (request["method"], request["path"]) == (
        "GET",
        "/api/v1/kanban/tasks",
    )
    assert request["query"] == {"limit": ["5"], "offset": ["2"]}
    assert "No tasks found." in result.stdout


def test_kanban_get_reads_task_by_uuid(api_server: Any) -> None:
    """Read a shared board task by the UUID returned when it was created."""
    task_id = "00000000-0000-0000-0000-000000000099"
    result = _invoke(api_server, ["kanban", "get", task_id])

    assert result.exit_code == 0, result.output
    assert api_server.requests[0]["method"] == "GET"
    assert api_server.requests[0]["path"] == f"/api/v1/kanban/tasks/{task_id}"
    assert "Review the demo" in result.stdout


def test_create_requires_nonblank_title_without_calling_api(api_server: Any) -> None:
    """Reject an empty title before sending a request."""
    result = _invoke(api_server, ["create", "--title", "   "])

    assert result.exit_code != 0
    assert "cannot be empty" in result.output
    assert api_server.requests == []


@pytest.mark.parametrize(
    "arguments",
    [
        ["create", "--title", "Work", "--status", "blocked"],
        ["create", "--title", "Work", "--priority", "urgent"],
        ["create", "--title", "Work", "--due-at", "2026-10-20T09:00:00"],
        ["list", "--status", "blocked"],
        ["list", "--limit", "0"],
        ["list", "--offset", "-1"],
    ],
)
def test_invalid_choices_dates_and_page_values_are_rejected(
    api_server: Any, arguments: list[str]
) -> None:
    """Reject values that the API cannot accept before sending a request."""
    result = _invoke(api_server, arguments)

    assert result.exit_code != 0
    assert api_server.requests == []


def test_create_reports_api_validation_error(api_server: Any) -> None:
    """Report a validation error returned by the API."""
    result = _invoke(api_server, ["create", "--title", "trigger-422"])

    assert result.exit_code != 0
    assert "HTTP 422" in result.stderr
    assert "Invalid title" in result.stderr


def test_list_passes_filters_and_pagination(api_server: Any) -> None:
    """List sends each documented filter as a query parameter."""
    result = _invoke(
        api_server,
        [
            "list",
            "--status",
            "assigned",
            "--status",
            "in_progress",
            "--assignee",
            "Jin",
            "--priority",
            "high",
            "--due-from",
            "2026-10-01T00:00:00Z",
            "--due-to",
            "2026-10-31T23:59:59Z",
            "--tag",
            "work",
            "--label",
            "weekly",
            "--exclude-completed",
            "--limit",
            "10",
            "--offset",
            "20",
        ],
    )

    assert result.exit_code == 0, result.output
    request = api_server.requests[0]
    assert (request["method"], request["path"]) == ("GET", "/api/v1/tasks")
    assert request["query"] == {
        "status": ["assigned", "in_progress"],
        "assignee": ["Jin"],
        "priority": ["high"],
        "due_from": ["2026-10-01T00:00:00+00:00"],
        "due_to": ["2026-10-31T23:59:59+00:00"],
        "tag": ["work"],
        "label": ["weekly"],
        "include_completed": ["false"],
        "limit": ["10"],
        "offset": ["20"],
    }


def test_list_uses_api_defaults(api_server: Any) -> None:
    """List uses the documented first page and includes completed tasks."""
    result = _invoke(api_server, ["list"])

    assert result.exit_code == 0, result.output
    assert api_server.requests[0]["query"] == {
        "include_completed": ["true"],
        "limit": ["20"],
        "offset": ["0"],
    }


def test_environment_base_url_is_used_and_normalized(api_server: Any) -> None:
    """Use the environment address and remove a trailing API path and slash."""
    result = runner.invoke(
        app,
        ["list"],
        env={
            "TTODO_BASE_URL": (
                f"http://127.0.0.1:{api_server.server_address[1]}/api/v1/"
            )
        },
    )

    assert result.exit_code == 0, result.output
    assert api_server.requests[0]["path"] == "/api/v1/tasks"


def test_default_base_url_is_used(monkeypatch: pytest.MonkeyPatch) -> None:
    """Use the documented local server when no address is configured."""
    received: dict[str, str] = {}

    class ClientStub:
        def __init__(self, *, base_url: str, **_: Any) -> None:
            received["base_url"] = base_url

        def __enter__(self) -> ClientStub:
            return self

        def __exit__(self, *args: Any) -> None:
            return None

    def get_task_request(*, client: Any, task_id: int) -> Any:
        return SimpleNamespace(
            status_code=200,
            content=b'{"id":12,"title":"Example","status":"assigned",'
            b'"priority":"medium"}',
        )

    monkeypatch.delenv("TTODO_BASE_URL", raising=False)
    monkeypatch.setattr(cli, "Client", ClientStub)
    monkeypatch.setattr(cli, "get_task_request", get_task_request)
    result = runner.invoke(app, ["get", "12"])

    assert result.exit_code == 0, result.output
    assert received["base_url"] == "http://127.0.0.1:8000"


def test_invalid_base_url_is_rejected_before_request(api_server: Any) -> None:
    """Reject addresses without an HTTP scheme before contacting a server."""
    result = runner.invoke(app, ["--base-url", "localhost:8000", "list"])

    assert result.exit_code != 0
    assert api_server.requests == []


def test_detail_command_calls_task_detail_endpoint(api_server: Any) -> None:
    """Get uses the task ID in the detail path."""
    result = _invoke(api_server, ["get", "12"])

    assert result.exit_code == 0, result.output
    assert api_server.requests[0]["path"] == "/api/v1/tasks/12"
    assert api_server.requests[0]["method"] == "GET"
    assert "Send the report" in result.stdout


def test_update_sends_only_the_fields_that_were_provided(api_server: Any) -> None:
    """Update leaves omitted fields out of the PATCH body."""
    result = _invoke(api_server, ["update", "12", "--title", "New title"])

    assert result.exit_code == 0, result.output
    request = api_server.requests[0]
    assert (request["method"], request["path"]) == ("PATCH", "/api/v1/tasks/12")
    assert request["body"] == {"title": "New title"}


def test_update_can_clear_nullable_and_list_fields(api_server: Any) -> None:
    """Clear options send null for nullable fields and empty lists for arrays."""
    result = _invoke(
        api_server,
        [
            "update",
            "12",
            "--clear-description",
            "--clear-due-at",
            "--clear-assignees",
            "--clear-tags",
            "--clear-labels",
        ],
    )

    assert result.exit_code == 0, result.output
    assert api_server.requests[0]["body"] == {
        "description": None,
        "due_at": None,
        "assignees": [],
        "tags": [],
        "labels": [],
    }


def test_update_rejects_conflicting_clear_and_value_options(api_server: Any) -> None:
    """Conflicting options fail before the API is called."""
    result = _invoke(
        api_server,
        ["update", "12", "--description", "Note", "--clear-description"],
    )

    assert result.exit_code != 0
    assert api_server.requests == []


def test_update_requires_a_field_to_change(api_server: Any) -> None:
    """An empty update does not send an empty patch to the API."""
    result = _invoke(api_server, ["update", "12"])

    assert result.exit_code != 0
    assert api_server.requests == []


def test_delete_calls_soft_delete_endpoint(api_server: Any) -> None:
    """Delete calls the API operation that hides a task."""
    result = _invoke(api_server, ["delete", "12"])

    assert result.exit_code == 0, result.output
    assert (api_server.requests[0]["method"], api_server.requests[0]["path"]) == (
        "DELETE",
        "/api/v1/tasks/12",
    )


def test_deleted_lists_removed_tasks(api_server: Any) -> None:
    """Deleted uses its separate list endpoint and accepts page options."""
    result = _invoke(api_server, ["deleted", "--limit", "10", "--offset", "20"])

    assert result.exit_code == 0, result.output
    request = api_server.requests[0]
    assert (request["method"], request["path"]) == (
        "GET",
        "/api/v1/tasks/deleted",
    )
    assert request["query"] == {"limit": ["10"], "offset": ["20"]}
    assert "No tasks found" in result.stdout


def test_restore_calls_restore_endpoint(api_server: Any) -> None:
    """Restore sends the task ID to the restore operation."""
    result = _invoke(api_server, ["restore", "12"])

    assert result.exit_code == 0, result.output
    assert (api_server.requests[0]["method"], api_server.requests[0]["path"]) == (
        "POST",
        "/api/v1/tasks/12/restore",
    )


def test_json_option_prints_parseable_api_result(api_server: Any) -> None:
    """JSON mode prints the response body without a text wrapper."""
    result = _invoke(api_server, ["--json", "get", "12"])

    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == {
        "id": 12,
        "title": "Send the report",
        "status": "assigned",
        "priority": "medium",
    }


@pytest.mark.parametrize(
    "arguments",
    [
        ["create", "--title", "A task"],
        ["list"],
        ["get", "12"],
        ["update", "12", "--title", "A new title"],
        ["delete", "12"],
        ["deleted"],
        ["restore", "12"],
    ],
)
def test_json_success_output_is_parseable_for_every_command(
    api_server: Any, arguments: list[str]
) -> None:
    """Keep every command's successful JSON output machine-readable."""
    result = _invoke(api_server, ["--json", *arguments])

    assert result.exit_code == 0, result.stderr
    assert isinstance(json.loads(result.stdout), (dict, list))


def test_api_errors_are_written_to_stderr(api_server: Any) -> None:
    """An API error has a useful message and nonzero exit status."""
    result = _invoke(api_server, ["get", "404"])

    assert result.exit_code != 0
    assert result.stdout == ""
    assert "HTTP 404" in result.stderr
    assert "Task not found" in result.stderr


def test_invalid_list_filter_error_is_reported(api_server: Any) -> None:
    """The CLI handles a 400 response that is not declared in OpenAPI."""
    result = _invoke(api_server, ["list", "--tag", "trigger-400"])

    assert result.exit_code != 0
    assert "HTTP 400" in result.stderr


def test_server_error_is_reported_without_traceback(api_server: Any) -> None:
    """A server error is shown without exposing a Python traceback."""
    result = _invoke(api_server, ["list", "--tag", "trigger-500"])

    assert result.exit_code != 0
    assert "HTTP 500" in result.stderr
    assert "Traceback" not in result.stderr


def test_json_mode_keeps_api_errors_out_of_standard_output(api_server: Any) -> None:
    """JSON mode leaves standard output empty when the request fails."""
    result = _invoke(api_server, ["--json", "get", "404"])

    assert result.exit_code != 0
    assert result.stdout == ""
    assert "HTTP 404" in result.stderr


@pytest.mark.parametrize(
    "arguments",
    [
        ["get", "404"],
        ["update", "404", "--title", "New title"],
        ["delete", "404"],
        ["restore", "404"],
    ],
)
def test_missing_task_errors_are_reported_for_each_item_operation(
    api_server: Any, arguments: list[str]
) -> None:
    """All item operations report the API's not-found response."""
    result = _invoke(api_server, arguments)

    assert result.exit_code != 0
    assert "HTTP 404" in result.stderr


def test_update_reports_api_validation_error(api_server: Any) -> None:
    """Report a validation error returned by the update API."""
    result = _invoke(api_server, ["update", "12", "--title", "trigger-422"])

    assert result.exit_code != 0
    assert "HTTP 422" in result.stderr
    assert "Invalid title" in result.stderr


def test_command_line_base_url_overrides_environment(
    api_server: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Prefer the address written in the command over the saved address."""
    monkeypatch.setenv("TTODO_BASE_URL", "http://127.0.0.1:1")
    result = _invoke(api_server, ["list"])

    assert result.exit_code == 0, result.output
    assert api_server.requests[0]["path"] == "/api/v1/tasks"


def test_environment_base_url_is_used_when_option_is_missing(
    api_server: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Use the saved address if --base-url was not provided."""
    base_url = f"http://127.0.0.1:{api_server.server_address[1]}"
    monkeypatch.setenv("TTODO_BASE_URL", base_url)
    result = runner.invoke(app, ["list"])

    assert result.exit_code == 0, result.output
    assert api_server.requests[0]["path"] == "/api/v1/tasks"


def test_base_url_with_api_prefix_is_not_duplicated(api_server: Any) -> None:
    """Accept a server URL that already ends in /api/v1."""
    base_url = f"http://127.0.0.1:{api_server.server_address[1]}/api/v1"
    result = runner.invoke(app, ["--base-url", base_url, "get", "12"])

    assert result.exit_code == 0, result.output
    assert api_server.requests[0]["path"] == "/api/v1/tasks/12"


def test_unreachable_server_has_a_friendly_error() -> None:
    """Explain how to fix a failed connection without showing a traceback."""
    result = runner.invoke(app, ["--base-url", "http://127.0.0.1:1", "list"])

    assert result.exit_code != 0
    assert result.stdout == ""
    assert "Check that the server is running" in result.stderr
    assert "Traceback" not in result.stderr
