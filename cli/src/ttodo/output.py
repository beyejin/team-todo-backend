"""Render API results for people or other programs."""

from __future__ import annotations

import json
from typing import Any

import typer


def show(value: Any, *, json_output: bool) -> None:
    """Print an API result as JSON or a readable text summary."""
    if json_output:
        typer.echo(json.dumps(value, ensure_ascii=False))
        return
    if isinstance(value, dict) and isinstance(value.get("items"), list):
        items = value["items"]
        if not items:
            typer.echo("No tasks found.")
            return
        for item in items:
            typer.echo(_task_line(item))
        typer.echo(f"Showing {len(items)} of {value.get('total', len(items))} tasks.")
        return
    if isinstance(value, dict) and "id" in value and "title" in value:
        typer.echo(_task_line(value))
        for field in ("description", "due_at", "assignees", "tags", "labels"):
            if field in value and value[field] not in (None, []):
                typer.echo(f"{_label(field)}: {value[field]}")
        return
    typer.echo(str(value))


def _task_line(task: Any) -> str:
    """Format the main fields of one task."""
    if not isinstance(task, dict):
        return str(task)
    task_id = task.get("id", "?")
    title = task.get("title", "Untitled task")
    status = task.get("status", "unknown")
    if "issue_number" in task:
        return f"#{task['issue_number']} {title}  [{status}]"
    priority = task.get("priority", "unknown")
    return f"#{task_id} {title}  [{status}; {priority}]"


def _label(field: str) -> str:
    """Return a readable label for a task field."""
    return field.replace("_", " ").capitalize()
