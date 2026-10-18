"""Typer commands for the Team Todo API."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, Any
from urllib.parse import urlparse

import httpx
import typer

from ttodo.generated.api.default.create_task_api_v1_tasks_post import (
    sync_detailed as create_task_request,
)
from ttodo.generated.api.default.delete_task_api_v1_tasks_task_id_delete import (
    sync_detailed as delete_task_request,
)
from ttodo.generated.api.default.get_deleted_tasks_api_v1_tasks_deleted_get import (
    sync_detailed as get_deleted_tasks_request,
)
from ttodo.generated.api.default.get_task_detail_api_v1_tasks_task_id_get import (
    sync_detailed as get_task_request,
)
from ttodo.generated.api.default.get_tasks_api_v1_tasks_get import (
    sync_detailed as get_tasks_request,
)
from ttodo.generated.api.default.restore_task_api_v1_tasks_task_id_restore_post import (
    sync_detailed as restore_task_request,
)
from ttodo.generated.api.default.update_task_api_v1_tasks_task_id_patch import (
    sync_detailed as update_task_request,
)
from ttodo.generated.client import Client
from ttodo.generated.models.task_input import TaskInput
from ttodo.generated.models.task_patch import TaskPatch
from ttodo.generated.types import Response
from ttodo.output import show

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
VALID_STATUSES = {"assigned", "in_progress", "completed"}
VALID_PRIORITIES = {"low", "medium", "high"}


@dataclass(frozen=True)
class Settings:
    """Settings shared by all CLI commands."""

    base_url: str
    json_output: bool
    api_token: str | None


app = typer.Typer(
    no_args_is_help=True,
    help=(
        "Manage tasks with your Team Todo server. The default server is "
        "http://127.0.0.1:8000. Use --base-url to choose another server and "
        "--json to print results for another program.\n\n"
        "Start with: ttodo list\n"
        'Create a task: ttodo create --title "Send the report"\n'
        "Print JSON: ttodo --json list"
    ),
)
kanban_app = typer.Typer(
    no_args_is_help=True,
    help="Create and browse tasks in the existing shared Team 6 Kanban board.",
)


def configure(
    context: typer.Context,
    base_url: Annotated[
        str,
        typer.Option(
            "--base-url",
            envvar="TTODO_BASE_URL",
            help="Address of your Todo server. Defaults to http://127.0.0.1:8000.",
        ),
    ] = DEFAULT_BASE_URL,
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Print the result as JSON so another program can read it.",
        ),
    ] = False,
) -> None:
    """Manage tasks on your Team Todo server."""
    normalized = base_url.rstrip("/")
    if normalized.endswith("/api/v1"):
        normalized = normalized[: -len("/api/v1")]
    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise typer.BadParameter(
            "Use a full server address, such as http://127.0.0.1:8000."
        )
    context.obj = Settings(
        base_url=normalized,
        json_output=json_output,
        api_token=os.environ.get("TTODO_API_TOKEN"),
    )


def create(
    context: typer.Context,
    title: Annotated[str, typer.Option(help="The task title. This is required.")],
    description: Annotated[
        str | None, typer.Option(help="A short note about the task.")
    ] = None,
    status: Annotated[
        str | None,
        typer.Option(help="Task status: assigned, in_progress, or completed."),
    ] = None,
    priority: Annotated[
        str | None, typer.Option(help="Task priority: low, medium, or high.")
    ] = None,
    due_at: Annotated[
        str | None,
        typer.Option(
            help="Due date with a time zone, such as 2026-10-20T09:00:00+09:00."
        ),
    ] = None,
    assignee: Annotated[
        list[str] | None,
        typer.Option(
            help="A person's name. Repeat this option to add more than one person."
        ),
    ] = None,
    tag: Annotated[
        list[str] | None,
        typer.Option(help="A tag for the task. Repeat this option to add more tags."),
    ] = None,
    label: Annotated[
        list[str] | None,
        typer.Option(
            help="A label for the task. Repeat this option to add more labels."
        ),
    ] = None,
) -> None:
    """Create a task.

    A title is required. If you leave out status or priority, the server uses
    its usual values. Repeat --assignee, --tag, or --label to add more items.

    Example: ttodo create --title "Send the report" --assignee "Jin"
    JSON example: ttodo --json create --title "Send the report"
    """
    body: dict[str, object] = {"title": _required_text(title, "title")}
    if description is not None:
        body["description"] = description
    if status is not None:
        body["status"] = _choice(status, VALID_STATUSES, "status")
    if priority is not None:
        body["priority"] = _choice(priority, VALID_PRIORITIES, "priority")
    if due_at is not None:
        body["due_at"] = _date_time(due_at, "due-at")
    if assignee is not None:
        body["assignees"] = assignee
    if tag is not None:
        body["tags"] = tag
    if label is not None:
        body["labels"] = label
    model = TaskInput.from_dict(body)
    result = _request(context, create_task_request, body=model)
    show(result, json_output=_settings(context).json_output)


def list_tasks(
    context: typer.Context,
    status: Annotated[
        list[str] | None,
        typer.Option(
            help="Show tasks with this status. Repeat for more than one status."
        ),
    ] = None,
    assignee: Annotated[
        str | None, typer.Option(help="Show tasks assigned to this person.")
    ] = None,
    priority: Annotated[
        str | None, typer.Option(help="Show tasks with this priority.")
    ] = None,
    due_from: Annotated[
        str | None,
        typer.Option(
            help="Show tasks due on or after this date and time, including a time zone."
        ),
    ] = None,
    due_to: Annotated[
        str | None,
        typer.Option(
            help="Show tasks due by this date and time, including a time zone."
        ),
    ] = None,
    tag: Annotated[str | None, typer.Option(help="Show tasks with this tag.")] = None,
    label: Annotated[
        str | None, typer.Option(help="Show tasks with this label.")
    ] = None,
    include_completed: Annotated[
        bool,
        typer.Option(
            "--include-completed/--exclude-completed",
            help="Include finished tasks. This is the default.",
        ),
    ] = True,
    limit: Annotated[
        int,
        typer.Option(
            min=1,
            max=100,
            help="How many tasks to show, from 1 to 100. Defaults to 20.",
        ),
    ] = 20,
    offset: Annotated[
        int, typer.Option(min=0, help="How many matching tasks to skip. Defaults to 0.")
    ] = 0,
) -> None:
    """Find active tasks by status, person, due date, tag, or label.

    The list includes finished tasks and shows up to 20 results by default.
    Use --exclude-completed to hide finished tasks.

    Example: ttodo list --status in_progress
    JSON example: ttodo --json list --limit 10
    """
    query: dict[str, object] = {
        "include_completed": include_completed,
        "limit": limit,
        "offset": offset,
    }
    if status:
        query["status"] = [_choice(item, VALID_STATUSES, "status") for item in status]
    for name, value in (
        ("assignee", assignee),
        ("priority", priority),
        ("due_from", due_from),
        ("due_to", due_to),
        ("tag", tag),
        ("label", label),
    ):
        if value is not None:
            query[name] = (
                _choice(value, VALID_PRIORITIES, name) if name == "priority" else value
            )
    for name in ("due_from", "due_to"):
        if name in query:
            query[name] = _date_time(str(query[name]), name.replace("_", "-"))
    result = _request(context, get_tasks_request, **query)
    show(result, json_output=_settings(context).json_output)


def get(
    context: typer.Context,
    task_id: Annotated[
        int, typer.Argument(min=1, help="The number of the task to show.")
    ],
) -> None:
    """Show all details for one active task.

    Example: ttodo get 12
    JSON example: ttodo --json get 12
    """
    result = _request(context, get_task_request, task_id=task_id)
    show(result, json_output=_settings(context).json_output)


def update(
    context: typer.Context,
    task_id: Annotated[
        int, typer.Argument(min=1, help="The number of the task to change.")
    ],
    title: Annotated[str | None, typer.Option(help="Replace the task title.")] = None,
    description: Annotated[
        str | None, typer.Option(help="Replace the task note.")
    ] = None,
    status: Annotated[
        str | None,
        typer.Option(help="Set status to assigned, in_progress, or completed."),
    ] = None,
    priority: Annotated[
        str | None, typer.Option(help="Set priority to low, medium, or high.")
    ] = None,
    due_at: Annotated[
        str | None, typer.Option(help="Set a due date and time, including a time zone.")
    ] = None,
    assignee: Annotated[
        list[str] | None,
        typer.Option(
            help="Replace the people assigned. Repeat to add more than one person."
        ),
    ] = None,
    tag: Annotated[
        list[str] | None,
        typer.Option(help="Replace the tags. Repeat to add more than one tag."),
    ] = None,
    label: Annotated[
        list[str] | None,
        typer.Option(help="Replace the labels. Repeat to add more than one label."),
    ] = None,
    clear_description: Annotated[
        bool, typer.Option(help="Remove the task note.")
    ] = False,
    clear_due_at: Annotated[bool, typer.Option(help="Remove the due date.")] = False,
    clear_assignees: Annotated[
        bool, typer.Option(help="Remove everyone assigned to the task.")
    ] = False,
    clear_tags: Annotated[bool, typer.Option(help="Remove all tags.")] = False,
    clear_labels: Annotated[bool, typer.Option(help="Remove all labels.")] = False,
) -> None:
    """Change only the task details you provide.

    Details you leave out stay the same. Repeating --assignee, --tag, or
    --label replaces that whole list. Use a --clear option to remove a value.

    Example: ttodo update 12 --title "New title"
    JSON example: ttodo --json update 12 --status completed
    """
    patch: dict[str, object] = {}
    for name, value in (
        ("title", title),
        ("description", description),
        ("status", status),
        ("priority", priority),
        ("due_at", due_at),
        ("assignees", assignee),
        ("tags", tag),
        ("labels", label),
    ):
        if value is not None:
            key = {"assignee": "assignees", "tag": "tags", "label": "labels"}.get(
                name, name
            )
            patch[key] = value
    clear_values = {
        "description": clear_description,
        "due_at": clear_due_at,
        "assignees": clear_assignees,
        "tags": clear_tags,
        "labels": clear_labels,
    }
    for name, clear in clear_values.items():
        if clear and name in patch:
            raise typer.BadParameter(
                f"Choose either a value or --clear-{name.replace('_', '-')}, not both."
            )
        if clear:
            patch[name] = [] if name in {"assignees", "tags", "labels"} else None
    if not patch:
        raise typer.BadParameter("Choose at least one task detail to change.")
    if "title" in patch:
        patch["title"] = _required_text(str(patch["title"]), "title")
    if "status" in patch:
        patch["status"] = _choice(str(patch["status"]), VALID_STATUSES, "status")
    if "priority" in patch:
        patch["priority"] = _choice(
            str(patch["priority"]), VALID_PRIORITIES, "priority"
        )
    if "due_at" in patch and patch["due_at"] is not None:
        patch["due_at"] = _date_time(str(patch["due_at"]), "due-at")
    model = TaskPatch.from_dict(patch)
    result = _request(context, update_task_request, task_id=task_id, body=model)
    show(result, json_output=_settings(context).json_output)


def delete(
    context: typer.Context,
    task_id: Annotated[
        int,
        typer.Argument(
            min=1, help="The number of the task to hide from the active list."
        ),
    ],
) -> None:
    """Hide a task from the active list without permanently removing it.

    You can find it with `ttodo deleted` and bring it back with
    `ttodo restore TASK_ID`.

    Example: ttodo delete 12
    JSON example: ttodo --json delete 12
    """
    result = _request(context, delete_task_request, task_id=task_id)
    show(result, json_output=_settings(context).json_output)


def deleted(
    context: typer.Context,
    limit: Annotated[
        int,
        typer.Option(
            min=1,
            max=100,
            help="How many deleted tasks to show, from 1 to 100. Defaults to 20.",
        ),
    ] = 20,
    offset: Annotated[
        int, typer.Option(min=0, help="How many deleted tasks to skip. Defaults to 0.")
    ] = 0,
) -> None:
    """Show tasks that were hidden from the active list.

    The command shows up to 20 results by default.

    Example: ttodo deleted --limit 10
    JSON example: ttodo --json deleted
    """
    result = _request(context, get_deleted_tasks_request, limit=limit, offset=offset)
    show(result, json_output=_settings(context).json_output)


def restore(
    context: typer.Context,
    task_id: Annotated[
        int, typer.Argument(min=1, help="The number of the deleted task to bring back.")
    ],
) -> None:
    """Bring a deleted task back to the active list.

    Example: ttodo restore 12
    JSON example: ttodo --json restore 12
    """
    result = _request(context, restore_task_request, task_id=task_id)
    show(result, json_output=_settings(context).json_output)


def create_kanban_task(
    context: typer.Context,
    title: Annotated[str, typer.Option(help="The task title. This is required.")],
    description: Annotated[
        str | None, typer.Option(help="A short note about the task.")
    ] = None,
    status: Annotated[
        str,
        typer.Option(help="Board status: assigned, in_progress, or completed."),
    ] = "assigned",
    assignee: Annotated[
        list[str] | None,
        typer.Option(help="A team member's GitHub username. Repeat to add more."),
    ] = None,
    label: Annotated[
        list[str] | None,
        typer.Option(help="A project label. Repeat to add more labels."),
    ] = None,
) -> None:
    """Create a task directly on the shared Team 6 Kanban board.

    Example: ttodo kanban create --title "Review the demo" --assignee han-yejin
    """
    body: dict[str, object] = {
        "title": _required_text(title, "title"),
        "status": _choice(status, VALID_STATUSES, "status"),
    }
    if description is not None:
        body["description"] = description
    if assignee is not None:
        body["assignees"] = assignee
    if label is not None:
        body["labels"] = label
    result = _kanban_request(context, "POST", "/api/v1/kanban/tasks", json=body)
    show(result, json_output=_settings(context).json_output)


def list_kanban_tasks(
    context: typer.Context,
    limit: Annotated[int, typer.Option(min=1, max=100)] = 20,
    offset: Annotated[int, typer.Option(min=0)] = 0,
) -> None:
    """List tasks currently placed on the shared Team 6 Kanban board."""
    result = _kanban_request(
        context,
        "GET",
        "/api/v1/kanban/tasks",
        params={"limit": limit, "offset": offset},
    )
    show(result, json_output=_settings(context).json_output)


def get_kanban_task(
    context: typer.Context,
    task_id: Annotated[str, typer.Argument(help="The task UUID returned by create.")],
) -> None:
    """Show a task saved on the shared Team 6 Kanban board."""
    result = _kanban_request(context, "GET", f"/api/v1/kanban/tasks/{task_id}")
    show(result, json_output=_settings(context).json_output)


def main() -> None:
    """Run the command-line application."""
    app()


def _settings(context: typer.Context) -> Settings:
    """Return settings created by the root callback."""
    settings = context.find_root().obj
    if not isinstance(settings, Settings):
        raise RuntimeError("CLI settings were not initialized.")
    return settings


def _request(
    context: typer.Context,
    operation: Callable[..., Response[Any]],
    **parameters: Any,
) -> Any:
    """Call one generated API operation and handle its response."""
    settings = _settings(context)
    try:
        with Client(
            base_url=settings.base_url,
            headers={"Authorization": f"Bearer {settings.api_token}"}
            if settings.api_token
            else {},
            timeout=5.0,
            raise_on_unexpected_status=False,
        ) as client:
            response = operation(client=client, **parameters)
    except httpx.HTTPError as error:
        typer.echo(
            f"Could not reach the Todo server at {settings.base_url}. "
            "Check that the server is running and try again.",
            err=True,
        )
        raise typer.Exit(code=1) from error
    body = _response_body(response.content)
    if not 200 <= int(response.status_code) < 300:
        detail = body.get("detail") if isinstance(body, dict) else body
        typer.echo(
            f"The server returned HTTP {int(response.status_code)}: "
            f"{_format_detail(detail)}",
            err=True,
        )
        raise typer.Exit(code=1)
    return body


def _kanban_request(
    context: typer.Context,
    method: str,
    path: str,
    **parameters: Any,
) -> Any:
    """Call a shared Kanban route and report errors using normal CLI rules."""
    settings = _settings(context)
    headers = (
        {"Authorization": f"Bearer {settings.api_token}"} if settings.api_token else {}
    )
    try:
        response = httpx.request(
            method,
            f"{settings.base_url}{path}",
            headers=headers,
            timeout=5.0,
            **parameters,
        )
    except httpx.HTTPError as error:
        typer.echo(
            f"Could not reach the Todo server at {settings.base_url}. "
            "Check that the server is running and try again.",
            err=True,
        )
        raise typer.Exit(code=1) from error
    body = _response_body(response.content)
    if not response.is_success:
        detail = body.get("detail") if isinstance(body, dict) else body
        typer.echo(
            f"The server returned HTTP {response.status_code}: "
            f"{_format_detail(detail)}",
            err=True,
        )
        raise typer.Exit(code=1)
    return body


def _response_body(content: bytes) -> Any:
    """Decode a JSON response while allowing empty response bodies."""
    if not content:
        return None
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return content.decode("utf-8", errors="replace")


def _format_detail(detail: Any) -> str:
    """Turn API validation errors into short, readable text."""
    if isinstance(detail, list):
        messages = []
        for item in detail:
            if isinstance(item, dict):
                location = ".".join(str(part) for part in item.get("loc", []))
                message = str(item.get("msg", "Invalid value"))
                messages.append(f"{location}: {message}" if location else message)
        return "; ".join(messages) or "The request could not be completed."
    if detail is None:
        return "The request could not be completed."
    return str(detail)


def _required_text(value: str, name: str) -> str:
    """Reject missing-looking or whitespace-only text values."""
    cleaned = value.strip()
    if not cleaned:
        raise typer.BadParameter(f"{name.capitalize()} cannot be empty.")
    return cleaned


def _choice(value: str, allowed: set[str], name: str) -> str:
    """Check a value against the API's accepted choices."""
    if value not in allowed:
        choices = ", ".join(sorted(allowed))
        raise typer.BadParameter(f"Choose a {name} from: {choices}.")
    return value


def _date_time(value: str, name: str) -> datetime:
    """Parse an ISO date and require a time-zone offset."""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise typer.BadParameter(f"{name} must be an ISO date and time.") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise typer.BadParameter(
            f"{name} must include a time zone, such as +09:00 or Z."
        )
    return parsed


app.callback()(configure)
app.command("create")(create)
app.command("list")(list_tasks)
app.command("get")(get)
app.command("update")(update)
app.command("delete")(delete)
app.command("deleted")(deleted)
app.command("restore")(restore)
kanban_app.command("create")(create_kanban_task)
kanban_app.command("list")(list_kanban_tasks)
kanban_app.command("get")(get_kanban_task)
app.add_typer(kanban_app, name="kanban")
