"""Create, read and move tasks in the existing shared Kanban schema."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Literal, cast
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.db import DatabaseConnection, Row, connect_postgres
from app.settings import get_setting

BoardStatus = Literal["assigned", "in_progress", "completed"]
STATUS_CATEGORIES = {
    "assigned": "todo",
    "in_progress": "in_progress",
    "completed": "done",
}


def clean_values(values: list[str]) -> list[str]:
    """Trim values and remove blanks and duplicates while preserving order."""
    return list(dict.fromkeys(value.strip() for value in values if value.strip()))


class BoardTaskInput(BaseModel):
    """Input fields supported by the existing Kanban issue schema."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    description: str | None = None
    status: BoardStatus = "assigned"
    assignees: list[str] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)

    @field_validator("title")
    @classmethod
    def nonblank_title(cls, value: str) -> str:
        """Reject whitespace-only task titles."""
        value = value.strip()
        if not value:
            raise ValueError("제목은 공백일 수 없습니다.")
        return value

    @field_validator("assignees", "labels")
    @classmethod
    def normalized_names(cls, value: list[str]) -> list[str]:
        """Normalize assigned GitHub usernames and project labels."""
        return clean_values(value)


class BoardTaskStatusPatch(BaseModel):
    """Require one supported status without allowing unrelated issue edits."""

    model_config = ConfigDict(extra="forbid")

    status: BoardStatus


@contextmanager
def kanban_database() -> Iterator[DatabaseConnection]:
    """Open the configured existing Kanban DB without creating parallel tables."""
    database_url = get_setting("KANBAN_DATABASE_URL")
    if not database_url:
        raise HTTPException(
            status_code=503, detail="공유 칸반 데이터베이스가 설정되지 않았습니다."
        )
    connection = connect_postgres(database_url, apply_migrations=False)
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def board_configuration() -> tuple[str, str]:
    """Return the configured board and author profile IDs."""
    board_id = get_setting("KANBAN_BOARD_ID")
    actor_id = get_setting("KANBAN_ACTOR_PROFILE_ID")
    if not board_id or not actor_id:
        raise HTTPException(
            status_code=503, detail="공유 칸반 보드 또는 작성자 설정이 없습니다."
        )
    try:
        UUID(board_id)
        UUID(actor_id)
    except ValueError as error:
        raise HTTPException(
            status_code=503, detail="공유 칸반 보드 설정이 올바르지 않습니다."
        ) from error
    return board_id, actor_id


def board_context(
    connection: DatabaseConnection, board_id: str, actor_id: str
) -> tuple[str, str]:
    """Return the board project and workspace if the author belongs to it."""
    row = connection.execute(
        "SELECT boards.project_id, projects.workspace_id "
        "FROM boards JOIN projects ON projects.id = boards.project_id "
        "JOIN workspace_members "
        "ON workspace_members.workspace_id = projects.workspace_id "
        "WHERE boards.id = ? AND workspace_members.profile_id = ?",
        (board_id, actor_id),
    ).fetchone()
    if row is None:
        raise HTTPException(
            status_code=403, detail="작성자가 공유 칸반 보드의 멤버가 아닙니다."
        )
    return str(row["project_id"]), str(row["workspace_id"])


def task_dict(connection: DatabaseConnection, row: Row) -> dict[str, object]:
    """Build the API representation from issue and board placement rows."""
    task_id = cast(UUID, row["id"])
    result = {
        "id": str(task_id),
        "issue_number": row["issue_number"],
        "title": row["title"],
        "description": row["description"],
        "status": {
            "todo": "assigned",
            "in_progress": "in_progress",
            "done": "completed",
        }[cast(str, row["category"])],
        "board_id": str(row["board_id"]),
        "column_id": str(row["column_id"]),
        "position": row["position"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
    result["assignees"] = [
        item["github_username"]
        for item in connection.execute(
            "SELECT profiles.github_username FROM issue_assignees "
            "JOIN profiles ON profiles.id = issue_assignees.profile_id "
            "WHERE issue_assignees.issue_id = ? ORDER BY profiles.github_username",
            (task_id,),
        ).fetchall()
    ]
    result["labels"] = [
        item["name"]
        for item in connection.execute(
            "SELECT labels.name FROM issue_labels "
            "JOIN labels ON labels.id = issue_labels.label_id "
            "WHERE issue_labels.issue_id = ? ORDER BY labels.name",
            (task_id,),
        ).fetchall()
    ]
    return result


router = APIRouter(prefix="/api/v1/kanban/tasks", tags=["kanban"])


@router.post("", status_code=201)
def create_board_task(payload: BoardTaskInput) -> dict[str, object]:
    """Create an issue and place it in the configured board column."""
    board_id, actor_id = board_configuration()
    with kanban_database() as connection:
        project_id, workspace_id = board_context(connection, board_id, actor_id)
        category = STATUS_CATEGORIES[payload.status]
        column = connection.execute(
            "SELECT board_columns.id FROM board_columns "
            "JOIN workflow_statuses "
            "ON workflow_statuses.id = board_columns.workflow_status_id "
            "WHERE board_columns.board_id = ? AND workflow_statuses.category = ? "
            "ORDER BY board_columns.position LIMIT 1",
            (board_id, category),
        ).fetchone()
        if column is None:
            raise HTTPException(
                status_code=409, detail="요청한 상태에 해당하는 보드 칼럼이 없습니다."
            )
        connection.execute(
            "SELECT pg_advisory_xact_lock(hashtext(?)::bigint)",
            (f"kanban-project:{project_id}",),
        )
        issue_row = connection.execute(
            "SELECT COALESCE(MAX(issue_number), 0) + 1 AS issue_number "
            "FROM issues WHERE project_id = ?",
            (project_id,),
        ).fetchone()
        if issue_row is None:
            raise RuntimeError("새 작업 번호를 확인할 수 없습니다.")
        issue_number = cast(int, issue_row["issue_number"])
        created = connection.execute(
            "INSERT INTO issues(project_id, issue_number, title, description, "
            "created_by) "
            "VALUES (?, ?, ?, ?, ?) RETURNING id",
            (project_id, issue_number, payload.title, payload.description, actor_id),
        ).fetchone()
        if created is None:
            raise RuntimeError("새 작업 ID를 확인할 수 없습니다.")
        task_id = cast(UUID, created["id"])
        column_id = str(column["id"])
        position_row = connection.execute(
            "SELECT COALESCE(MAX(position), -1) + 1 AS position "
            "FROM board_items WHERE column_id = ?",
            (column_id,),
        ).fetchone()
        if position_row is None:
            raise RuntimeError("보드 칼럼 위치를 확인할 수 없습니다.")
        position = cast(int, position_row["position"])
        connection.execute(
            "INSERT INTO board_items(board_id, issue_id, column_id, position) "
            "VALUES (?, ?, ?, ?)",
            (board_id, task_id, column_id, position),
        )
        for username in payload.assignees:
            profile = connection.execute(
                "SELECT profiles.id FROM profiles "
                "JOIN workspace_members ON workspace_members.profile_id = profiles.id "
                "WHERE workspace_members.workspace_id = ? "
                "AND profiles.github_username = ?",
                (workspace_id, username),
            ).fetchone()
            if profile is None:
                raise HTTPException(
                    status_code=422,
                    detail=f"팀 멤버를 찾을 수 없습니다: {username}",
                )
            connection.execute(
                "INSERT INTO issue_assignees(issue_id, profile_id) VALUES (?, ?)",
                (task_id, profile["id"]),
            )
        for label_name in payload.labels:
            label = connection.execute(
                "INSERT INTO labels(project_id, name, color) VALUES (?, ?, '#64748B') "
                "ON CONFLICT (project_id, name) DO UPDATE SET name = EXCLUDED.name "
                "RETURNING id",
                (project_id, label_name),
            ).fetchone()
            if label is None:
                raise RuntimeError("라벨 ID를 확인할 수 없습니다.")
            connection.execute(
                "INSERT INTO issue_labels(issue_id, label_id) VALUES (?, ?)",
                (task_id, label["id"]),
            )
        row = connection.execute(
            "SELECT issues.id, issues.issue_number, issues.title, issues.description, "
            "issues.created_at, issues.updated_at, board_items.board_id, "
            "board_items.column_id, board_items.position, workflow_statuses.category "
            "FROM issues JOIN board_items ON board_items.issue_id = issues.id "
            "JOIN board_columns ON board_columns.id = board_items.column_id "
            "JOIN workflow_statuses "
            "ON workflow_statuses.id = board_columns.workflow_status_id "
            "WHERE issues.id = ? AND board_items.board_id = ?",
            (task_id, board_id),
        ).fetchone()
        if row is None:
            raise RuntimeError("보드에 추가된 작업을 확인할 수 없습니다.")
        return task_dict(connection, row)


@router.get("")
def list_board_tasks(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> dict[str, object]:
    """List tasks in the configured board in column and position order."""
    board_id, actor_id = board_configuration()
    with kanban_database() as connection:
        board_context(connection, board_id, actor_id)
        count_row = connection.execute(
            "SELECT count(*) AS total FROM board_items WHERE board_id = ?",
            (board_id,),
        ).fetchone()
        if count_row is None:
            raise RuntimeError("보드 작업 개수를 확인할 수 없습니다.")
        rows = connection.execute(
            "SELECT issues.id, issues.issue_number, issues.title, issues.description, "
            "issues.created_at, issues.updated_at, board_items.board_id, "
            "board_items.column_id, board_items.position, workflow_statuses.category "
            "FROM board_items JOIN issues ON issues.id = board_items.issue_id "
            "JOIN board_columns ON board_columns.id = board_items.column_id "
            "JOIN workflow_statuses "
            "ON workflow_statuses.id = board_columns.workflow_status_id "
            "WHERE board_items.board_id = ? "
            "ORDER BY board_columns.position, board_items.position, "
            "issues.issue_number "
            "LIMIT ? OFFSET ?",
            (board_id, limit, offset),
        ).fetchall()
        return {
            "items": [task_dict(connection, row) for row in rows],
            "total": cast(int, count_row["total"]),
            "limit": limit,
            "offset": offset,
        }


@router.get("/{task_id}")
def get_board_task(task_id: UUID) -> dict[str, object]:
    """Read one issue only when it is placed on the configured board."""
    board_id, actor_id = board_configuration()
    with kanban_database() as connection:
        board_context(connection, board_id, actor_id)
        row = connection.execute(
            "SELECT issues.id, issues.issue_number, issues.title, issues.description, "
            "issues.created_at, issues.updated_at, board_items.board_id, "
            "board_items.column_id, board_items.position, workflow_statuses.category "
            "FROM issues JOIN board_items ON board_items.issue_id = issues.id "
            "JOIN board_columns ON board_columns.id = board_items.column_id "
            "JOIN workflow_statuses "
            "ON workflow_statuses.id = board_columns.workflow_status_id "
            "WHERE issues.id = ? AND board_items.board_id = ?",
            (task_id, board_id),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="보드 작업을 찾을 수 없습니다.")
        return task_dict(connection, row)


@router.patch("/{task_id}")
def update_board_task_status(
    task_id: UUID, payload: BoardTaskStatusPatch
) -> dict[str, object]:
    """Move a board issue to the end of a status column in one transaction."""
    board_id, actor_id = board_configuration()
    with kanban_database() as connection:
        project_id, _ = board_context(connection, board_id, actor_id)
        # Share creation's lock so concurrent inserts and moves cannot reuse a position.
        connection.execute(
            "SELECT pg_advisory_xact_lock(hashtext(?)::bigint)",
            (f"kanban-project:{project_id}",),
        )
        row = connection.execute(
            "SELECT issues.id, issues.issue_number, issues.title, issues.description, "
            "issues.created_at, issues.updated_at, board_items.board_id, "
            "board_items.column_id, board_items.position, workflow_statuses.category "
            "FROM issues JOIN board_items ON board_items.issue_id = issues.id "
            "JOIN board_columns ON board_columns.id = board_items.column_id "
            "JOIN workflow_statuses "
            "ON workflow_statuses.id = board_columns.workflow_status_id "
            "WHERE issues.id = ? AND board_items.board_id = ? "
            "FOR UPDATE OF issues, board_items",
            (task_id, board_id),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="보드 작업을 찾을 수 없습니다.")
        category = STATUS_CATEGORIES[payload.status]
        if row["category"] == category:
            return task_dict(connection, row)
        column = connection.execute(
            "SELECT board_columns.id FROM board_columns "
            "JOIN workflow_statuses "
            "ON workflow_statuses.id = board_columns.workflow_status_id "
            "WHERE board_columns.board_id = ? AND workflow_statuses.category = ? "
            "ORDER BY board_columns.position LIMIT 1",
            (board_id, category),
        ).fetchone()
        if column is None:
            raise HTTPException(
                status_code=409, detail="요청한 상태에 해당하는 보드 칼럼이 없습니다."
            )
        column_id = str(column["id"])
        position_row = connection.execute(
            "SELECT COALESCE(MAX(position), -1) + 1 AS position "
            "FROM board_items WHERE column_id = ?",
            (column_id,),
        ).fetchone()
        if position_row is None:
            raise RuntimeError("보드 칼럼 위치를 확인할 수 없습니다.")
        position = cast(int, position_row["position"])
        connection.execute(
            "UPDATE board_items SET column_id = ?, position = ?, "
            "updated_at = clock_timestamp() WHERE board_id = ? AND issue_id = ?",
            (column_id, position, board_id, task_id),
        )
        updated = connection.execute(
            "UPDATE issues SET updated_at = clock_timestamp() WHERE id = ? "
            "RETURNING updated_at",
            (task_id,),
        ).fetchone()
        if updated is None:
            raise RuntimeError("변경한 작업의 수정 시각을 확인할 수 없습니다.")
        result = task_dict(connection, row)
        result.update(
            status=payload.status,
            column_id=column_id,
            position=position,
            updated_at=updated["updated_at"],
        )
        return result
