"""Keep the CLI routes aligned with every operation in the saved OpenAPI spec."""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any

from ttodo.cli import app

OPENAPI_PATH = Path(__file__).parents[1] / "openapi.json"
EXPECTED_OPERATIONS = {
    ("post", "/api/v1/tasks", "create_task_api_v1_tasks_post"),
    ("get", "/api/v1/tasks", "get_tasks_api_v1_tasks_get"),
    ("get", "/api/v1/tasks/{task_id}", "get_task_detail_api_v1_tasks__task_id__get"),
    ("patch", "/api/v1/tasks/{task_id}", "update_task_api_v1_tasks__task_id__patch"),
    ("delete", "/api/v1/tasks/{task_id}", "delete_task_api_v1_tasks__task_id__delete"),
    ("get", "/api/v1/tasks/deleted", "get_deleted_tasks_api_v1_tasks_deleted_get"),
    (
        "post",
        "/api/v1/tasks/{task_id}/restore",
        "restore_task_api_v1_tasks__task_id__restore_post",
    ),
}

CLI_INPUTS = {
    "create_task_api_v1_tasks_post": {
        "title": "title",
        "description": "description",
        "status": "status",
        "priority": "priority",
        "due_at": "due_at",
        "assignees": "assignee",
        "tags": "tag",
        "labels": "label",
    },
    "get_tasks_api_v1_tasks_get": {
        "status": "status",
        "assignee": "assignee",
        "priority": "priority",
        "due_from": "due_from",
        "due_to": "due_to",
        "tag": "tag",
        "label": "label",
        "include_completed": "include_completed",
        "limit": "limit",
        "offset": "offset",
    },
    "get_task_detail_api_v1_tasks__task_id__get": {"task_id": "task_id"},
    "update_task_api_v1_tasks__task_id__patch": {
        "task_id": "task_id",
        "title": "title",
        "description": "description",
        "status": "status",
        "priority": "priority",
        "due_at": "due_at",
        "assignees": "assignee",
        "tags": "tag",
        "labels": "label",
    },
    "delete_task_api_v1_tasks__task_id__delete": {"task_id": "task_id"},
    "get_deleted_tasks_api_v1_tasks_deleted_get": {
        "limit": "limit",
        "offset": "offset",
    },
    "restore_task_api_v1_tasks__task_id__restore_post": {"task_id": "task_id"},
}


def test_saved_openapi_has_exactly_the_supported_task_operations() -> None:
    """Fail when the API adds or removes an operation without CLI coverage."""
    schema = json.loads(OPENAPI_PATH.read_text())
    operations: set[tuple[str, str, str]] = set()
    for path, path_item in schema["paths"].items():
        for method, operation in path_item.items():
            if method.lower() in {"get", "post", "patch", "delete"}:
                operation_id: Any = operation.get("operationId")
                operations.add((method.lower(), path, operation_id))

    assert operations == EXPECTED_OPERATIONS


def test_every_openapi_input_is_exposed_by_its_cli_command() -> None:
    """Track every API input to a real command argument or option."""
    schema = json.loads(OPENAPI_PATH.read_text())
    callbacks = {
        command.name: inspect.signature(command.callback).parameters
        for command in app.registered_commands
        if command.name and command.callback
    }
    expected_ids = {operation_id for _, _, operation_id in EXPECTED_OPERATIONS}

    for _path, path_item in schema["paths"].items():
        for method, operation in path_item.items():
            if method.lower() not in {"get", "post", "patch", "delete"}:
                continue
            operation_id = operation["operationId"]
            inputs = CLI_INPUTS[operation_id]
            command_name = {
                "create_task_api_v1_tasks_post": "create",
                "get_tasks_api_v1_tasks_get": "list",
                "get_task_detail_api_v1_tasks__task_id__get": "get",
                "update_task_api_v1_tasks__task_id__patch": "update",
                "delete_task_api_v1_tasks__task_id__delete": "delete",
                "get_deleted_tasks_api_v1_tasks_deleted_get": "deleted",
                "restore_task_api_v1_tasks__task_id__restore_post": "restore",
            }[operation_id]
            api_inputs = {
                parameter["name"] for parameter in operation.get("parameters", [])
            }
            request_body = operation.get("requestBody")
            if request_body:
                reference = request_body["content"]["application/json"]["schema"][
                    "$ref"
                ]
                model_name = reference.rsplit("/", maxsplit=1)[-1]
                api_inputs.update(
                    schema["components"]["schemas"][model_name]["properties"]
                )

            assert api_inputs == set(inputs), (operation_id, api_inputs, set(inputs))
            assert set(inputs.values()) <= set(callbacks[command_name]), operation_id

    assert set(CLI_INPUTS) == expected_ids
