"""Team Todo API application."""

from __future__ import annotations

import hmac
import os
from datetime import UTC, datetime
from typing import Annotated, Literal, cast

from fastapi import FastAPI, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

from app.db import DatabaseConnection, Row, database
from app.kanban import router as kanban_router

Status = Literal["assigned", "in_progress", "completed"]
Priority = Literal["low", "medium", "high"]


def now() -> str:
    """Return the current UTC time in ISO 8601 form."""
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def normalize_datetime(value: datetime | None) -> str | None:
    """Normalize a timezone-aware datetime to a UTC ISO 8601 string."""
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("날짜와 시각에는 시간대가 필요합니다.")
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def clean_values(values: list[str]) -> list[str]:
    """Trim values and remove blanks and duplicates while preserving order."""
    return list(dict.fromkeys(value.strip() for value in values if value.strip()))


class TaskInput(BaseModel):
    """Create or partially update task fields."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    description: str | None = None
    status: Status = "assigned"
    priority: Priority = "medium"
    due_at: datetime | None = None
    assignees: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)

    @field_validator("title")
    @classmethod
    def nonblank_title(cls, value: str) -> str:
        """Reject a title containing only whitespace and trim its edges."""
        value = value.strip()
        if not value:
            raise ValueError("제목은 공백일 수 없습니다.")
        return value

    @field_validator("due_at")
    @classmethod
    def aware_due_at(cls, value: datetime | None) -> datetime | None:
        """Require an explicit timezone for due dates."""
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("마감일에는 시간대가 필요합니다.")
        return value

    @field_validator("assignees", "tags", "labels")
    @classmethod
    def normalized_lists(cls, value: list[str]) -> list[str]:
        """Normalize each free-form string list."""
        return clean_values(value)


class TaskPatch(BaseModel):
    """Fields accepted by a partial task update."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    description: str | None = None
    status: Status | None = None
    priority: Priority | None = None
    due_at: datetime | None = None
    assignees: list[str] | None = None
    tags: list[str] | None = None
    labels: list[str] | None = None

    @field_validator("title")
    @classmethod
    def valid_title(cls, value: str | None) -> str | None:
        """Reject null and whitespace-only titles when supplied."""
        if value is None or not value.strip():
            raise ValueError("제목은 비어 있을 수 없습니다.")
        return value.strip()

    @field_validator("status", "priority")
    @classmethod
    def non_null_enums(cls, value: Status | Priority | None) -> Status | Priority:
        """Reject null for fields that have no nullable storage value."""
        if value is None:
            raise ValueError("상태와 우선순위는 null일 수 없습니다.")
        return value

    @field_validator("due_at")
    @classmethod
    def aware_due_at(cls, value: datetime | None) -> datetime | None:
        """Require timezone information for non-null due dates."""
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("마감일에는 시간대가 필요합니다.")
        return value

    @field_validator("assignees", "tags", "labels")
    @classmethod
    def normalized_lists(cls, value: list[str] | None) -> list[str] | None:
        """Normalize each supplied free-form string list."""
        return clean_values(value) if value is not None else None


def task_dict(connection: DatabaseConnection, row: Row) -> dict[str, object]:
    """Convert a task row and its relationships to the API representation."""
    task_id = cast(int, row["id"])
    result = {
        key: row[key]
        for key in (
            "id",
            "title",
            "description",
            "status",
            "priority",
            "due_at",
            "created_at",
            "updated_at",
            "deleted_at",
        )
    }
    for field, table, column in (
        ("assignees", "task_assignees", "assignee_name"),
        ("tags", "task_tags", "tag"),
        ("labels", "task_labels", "label"),
    ):
        result[field] = [
            item[column]
            for item in connection.execute(
                f"SELECT {column} FROM {table} WHERE task_id = ? "
                f"ORDER BY {'id' if connection.is_postgres else 'rowid'}",
                (task_id,),
            ).fetchall()
        ]
    return result


def replace_values(
    connection: DatabaseConnection,
    task_id: int,
    field: str,
    values: list[str],
) -> None:
    """Replace one task relationship list."""
    table, column = {
        "assignees": ("task_assignees", "assignee_name"),
        "tags": ("task_tags", "tag"),
        "labels": ("task_labels", "label"),
    }[field]
    connection.execute(f"DELETE FROM {table} WHERE task_id = ?", (task_id,))
    connection.executemany(
        f"INSERT INTO {table}(task_id, {column}) VALUES (?, ?)",
        [(task_id, value) for value in values],
    )


def get_task(connection: DatabaseConnection, task_id: int) -> Row:
    """Fetch an active task or raise 404."""
    row = connection.execute(
        "SELECT * FROM tasks WHERE id = ? AND deleted_at IS NULL", (task_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="할 일을 찾을 수 없습니다.")
    return row


app = FastAPI(title="Team Todo API", version="1.0.0")
app.include_router(kanban_router)


@app.middleware("http")
async def require_team_token(
    request: Request, call_next: RequestResponseEndpoint
) -> Response:
    """Require a bearer token on API routes when a shared token is configured."""
    expected_token = os.environ.get("TTODO_API_TOKEN")
    if request.url.path.startswith("/api/") and expected_token:
        authorization = request.headers.get("authorization", "")
        supplied_token = authorization.removeprefix("Bearer ")
        if not authorization.startswith("Bearer ") or not hmac.compare_digest(
            supplied_token, expected_token
        ):
            return JSONResponse(
                status_code=401,
                content={"detail": "유효한 API 토큰이 필요합니다."},
                headers={"WWW-Authenticate": "Bearer"},
            )
    return await call_next(request)


@app.post("/api/v1/tasks", status_code=201)
def create_task(payload: TaskInput) -> dict[str, object]:
    """Create a task with its assignees, tags, and labels."""
    timestamp = now()
    with database() as connection:
        cursor = connection.execute(
            "INSERT INTO tasks(title, description, status, priority, due_at, "
            "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)"
            + (" RETURNING id" if connection.is_postgres else ""),
            (
                payload.title,
                payload.description,
                payload.status,
                payload.priority,
                normalize_datetime(payload.due_at),
                timestamp,
                timestamp,
            ),
        )
        if connection.is_postgres:
            inserted = cursor.fetchone()
            if inserted is None:
                raise RuntimeError("생성된 할 일 ID를 확인할 수 없습니다.")
            task_id = cast(int, inserted["id"])
        else:
            if cursor.lastrowid is None:
                raise RuntimeError("생성된 할 일 ID를 확인할 수 없습니다.")
            task_id = cursor.lastrowid
        for field in ("assignees", "tags", "labels"):
            replace_values(connection, task_id, field, getattr(payload, field))
        row = connection.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        if row is None:
            raise RuntimeError("생성된 할 일을 확인할 수 없습니다.")
        return task_dict(connection, row)


def list_tasks(
    *,
    deleted: bool,
    statuses: list[str],
    assignee: str | None,
    priority: str | None,
    due_from: datetime | None,
    due_to: datetime | None,
    tag: str | None,
    label: str | None,
    include_completed: bool,
    limit: int,
    offset: int,
) -> dict[str, object]:
    """Return filtered tasks with pagination metadata."""
    clauses = ["deleted_at IS NOT NULL" if deleted else "deleted_at IS NULL"]
    parameters: list[object] = []
    if statuses:
        clauses.append(f"status IN ({','.join('?' for _ in statuses)})")
        parameters.extend(statuses)
    if not deleted and not include_completed:
        clauses.append("status != 'completed'")
    if priority:
        clauses.append("priority = ?")
        parameters.append(priority)
    if due_from:
        clauses.append("due_at >= ?")
        parameters.append(normalize_datetime(due_from))
    if due_to:
        clauses.append("due_at <= ?")
        parameters.append(normalize_datetime(due_to))
    for table, column, value in (
        ("task_assignees", "assignee_name", assignee),
        ("task_tags", "tag", tag),
        ("task_labels", "label", label),
    ):
        if value:
            clauses.append(
                f"EXISTS (SELECT 1 FROM {table} x WHERE x.task_id = tasks.id "
                f"AND x.{column} = ?)"
            )
            parameters.append(value.strip())
    where = " AND ".join(clauses)
    with database() as connection:
        total_row = connection.execute(
            f"SELECT count(*) AS total FROM tasks WHERE {where}", parameters
        ).fetchone()
        if total_row is None:
            raise RuntimeError("할 일 개수를 확인할 수 없습니다.")
        total = cast(int, total_row["total"])
        rows = connection.execute(
            f"SELECT * FROM tasks WHERE {where} ORDER BY created_at DESC, id DESC "
            "LIMIT ? OFFSET ?",
            [*parameters, limit, offset],
        ).fetchall()
        return {
            "items": [task_dict(connection, row) for row in rows],
            "total": total,
            "limit": limit,
            "offset": offset,
        }


@app.get("/api/v1/tasks")
def get_tasks(
    status: Annotated[list[str] | None, Query()] = None,
    assignee: str | None = None,
    priority: str | None = None,
    due_from: datetime | None = None,
    due_to: datetime | None = None,
    tag: str | None = None,
    label: str | None = None,
    include_completed: bool = True,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, object]:
    """List active tasks matching every supplied filter."""
    valid_statuses = {"assigned", "in_progress", "completed"}
    if status and any(value not in valid_statuses for value in status):
        raise HTTPException(status_code=400, detail="유효하지 않은 상태 필터입니다.")
    if priority and priority not in {"low", "medium", "high"}:
        raise HTTPException(
            status_code=400, detail="유효하지 않은 우선순위 필터입니다."
        )
    if any(
        value is not None and (value.tzinfo is None or value.utcoffset() is None)
        for value in (due_from, due_to)
    ):
        raise HTTPException(
            status_code=400, detail="마감일 필터에는 시간대가 필요합니다."
        )
    if due_from and due_to and due_from > due_to:
        raise HTTPException(status_code=400, detail="마감일 범위가 올바르지 않습니다.")
    return list_tasks(
        deleted=False,
        statuses=status or [],
        assignee=assignee,
        priority=priority,
        due_from=due_from,
        due_to=due_to,
        tag=tag,
        label=label,
        include_completed=include_completed,
        limit=limit,
        offset=offset,
    )


@app.get("/api/v1/tasks/deleted")
def get_deleted_tasks(
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, object]:
    """List soft-deleted tasks."""
    return list_tasks(
        deleted=True,
        statuses=[],
        assignee=None,
        priority=None,
        due_from=None,
        due_to=None,
        tag=None,
        label=None,
        include_completed=True,
        limit=limit,
        offset=offset,
    )


@app.get("/api/v1/tasks/{task_id}")
def get_task_detail(task_id: int) -> dict[str, object]:
    """Read one active task."""
    with database() as connection:
        return task_dict(connection, get_task(connection, task_id))


@app.patch("/api/v1/tasks/{task_id}")
def update_task(task_id: int, payload: TaskPatch) -> dict[str, object]:
    """Update only supplied task fields."""
    changes = payload.model_dump(exclude_unset=True)
    with database() as connection:
        get_task(connection, task_id)
        scalar_fields = {"title", "description", "status", "priority", "due_at"}
        values: dict[str, object] = {}
        for field, value in changes.items():
            if field in scalar_fields:
                values[field] = (
                    normalize_datetime(value) if field == "due_at" and value else value
                )
            elif value is not None:
                replace_values(connection, task_id, field, value)
        if values or changes:
            values["updated_at"] = now()
            assignments = ", ".join(f"{field} = ?" for field in values)
            connection.execute(
                f"UPDATE tasks SET {assignments} WHERE id = ?",
                [*values.values(), task_id],
            )
        row = get_task(connection, task_id)
        return task_dict(connection, row)


@app.delete("/api/v1/tasks/{task_id}")
def delete_task(task_id: int) -> dict[str, object]:
    """Soft-delete an active task."""
    with database() as connection:
        get_task(connection, task_id)
        timestamp = now()
        connection.execute(
            "UPDATE tasks SET deleted_at = ?, updated_at = ? WHERE id = ?",
            (timestamp, timestamp, task_id),
        )
        row = connection.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        if row is None:
            raise RuntimeError("삭제된 할 일을 확인할 수 없습니다.")
        return task_dict(connection, row)


@app.post("/api/v1/tasks/{task_id}/restore")
def restore_task(task_id: int) -> dict[str, object]:
    """Restore a soft-deleted task."""
    with database() as connection:
        row = connection.execute(
            "SELECT * FROM tasks WHERE id = ? AND deleted_at IS NOT NULL", (task_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(
                status_code=404, detail="삭제된 할 일을 찾을 수 없습니다."
            )
        connection.execute(
            "UPDATE tasks SET deleted_at = NULL, updated_at = ? WHERE id = ?",
            (now(), task_id),
        )
        restored = connection.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        if restored is None:
            raise RuntimeError("복구된 할 일을 확인할 수 없습니다.")
        return task_dict(connection, restored)
