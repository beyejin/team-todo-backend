from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...models.task_patch import TaskPatch
from ...models.update_task_api_v1_tasks_task_id_patch_response_update_task_api_v1_tasks_task_id_patch import (
    UpdateTaskApiV1TasksTaskIdPatchResponseUpdateTaskApiV1TasksTaskIdPatch,
)
from ...types import Response


def _get_kwargs(
    task_id: int,
    *,
    body: TaskPatch,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "patch",
        "url": "/api/v1/tasks/{task_id}".format(
            task_id=quote(str(task_id), safe=""),
        ),
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    HTTPValidationError
    | UpdateTaskApiV1TasksTaskIdPatchResponseUpdateTaskApiV1TasksTaskIdPatch
    | None
):
    if response.status_code == 200:
        response_200 = UpdateTaskApiV1TasksTaskIdPatchResponseUpdateTaskApiV1TasksTaskIdPatch.from_dict(
            response.json()
        )

        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())

        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
    HTTPValidationError
    | UpdateTaskApiV1TasksTaskIdPatchResponseUpdateTaskApiV1TasksTaskIdPatch
]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    task_id: int,
    *,
    client: AuthenticatedClient | Client,
    body: TaskPatch,
) -> Response[
    HTTPValidationError
    | UpdateTaskApiV1TasksTaskIdPatchResponseUpdateTaskApiV1TasksTaskIdPatch
]:
    """Update Task

     Update only supplied task fields.

    Args:
        task_id (int):
        body (TaskPatch): Fields accepted by a partial task update.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | UpdateTaskApiV1TasksTaskIdPatchResponseUpdateTaskApiV1TasksTaskIdPatch]
    """

    kwargs = _get_kwargs(
        task_id=task_id,
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    task_id: int,
    *,
    client: AuthenticatedClient | Client,
    body: TaskPatch,
) -> (
    HTTPValidationError
    | UpdateTaskApiV1TasksTaskIdPatchResponseUpdateTaskApiV1TasksTaskIdPatch
    | None
):
    """Update Task

     Update only supplied task fields.

    Args:
        task_id (int):
        body (TaskPatch): Fields accepted by a partial task update.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | UpdateTaskApiV1TasksTaskIdPatchResponseUpdateTaskApiV1TasksTaskIdPatch
    """

    return sync_detailed(
        task_id=task_id,
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    task_id: int,
    *,
    client: AuthenticatedClient | Client,
    body: TaskPatch,
) -> Response[
    HTTPValidationError
    | UpdateTaskApiV1TasksTaskIdPatchResponseUpdateTaskApiV1TasksTaskIdPatch
]:
    """Update Task

     Update only supplied task fields.

    Args:
        task_id (int):
        body (TaskPatch): Fields accepted by a partial task update.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | UpdateTaskApiV1TasksTaskIdPatchResponseUpdateTaskApiV1TasksTaskIdPatch]
    """

    kwargs = _get_kwargs(
        task_id=task_id,
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    task_id: int,
    *,
    client: AuthenticatedClient | Client,
    body: TaskPatch,
) -> (
    HTTPValidationError
    | UpdateTaskApiV1TasksTaskIdPatchResponseUpdateTaskApiV1TasksTaskIdPatch
    | None
):
    """Update Task

     Update only supplied task fields.

    Args:
        task_id (int):
        body (TaskPatch): Fields accepted by a partial task update.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | UpdateTaskApiV1TasksTaskIdPatchResponseUpdateTaskApiV1TasksTaskIdPatch
    """

    return (
        await asyncio_detailed(
            task_id=task_id,
            client=client,
            body=body,
        )
    ).parsed
