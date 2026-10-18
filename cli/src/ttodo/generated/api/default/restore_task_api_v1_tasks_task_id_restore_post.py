from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...models.restore_task_api_v1_tasks_task_id_restore_post_response_restore_task_api_v1_tasks_task_id_restore_post import (
    RestoreTaskApiV1TasksTaskIdRestorePostResponseRestoreTaskApiV1TasksTaskIdRestorePost,
)
from ...types import Response


def _get_kwargs(
    task_id: int,
) -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/v1/tasks/{task_id}/restore".format(
            task_id=quote(str(task_id), safe=""),
        ),
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    HTTPValidationError
    | RestoreTaskApiV1TasksTaskIdRestorePostResponseRestoreTaskApiV1TasksTaskIdRestorePost
    | None
):
    if response.status_code == 200:
        response_200 = RestoreTaskApiV1TasksTaskIdRestorePostResponseRestoreTaskApiV1TasksTaskIdRestorePost.from_dict(
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
    | RestoreTaskApiV1TasksTaskIdRestorePostResponseRestoreTaskApiV1TasksTaskIdRestorePost
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
) -> Response[
    HTTPValidationError
    | RestoreTaskApiV1TasksTaskIdRestorePostResponseRestoreTaskApiV1TasksTaskIdRestorePost
]:
    """Restore Task

     Restore a soft-deleted task.

    Args:
        task_id (int):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | RestoreTaskApiV1TasksTaskIdRestorePostResponseRestoreTaskApiV1TasksTaskIdRestorePost]
    """

    kwargs = _get_kwargs(
        task_id=task_id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    task_id: int,
    *,
    client: AuthenticatedClient | Client,
) -> (
    HTTPValidationError
    | RestoreTaskApiV1TasksTaskIdRestorePostResponseRestoreTaskApiV1TasksTaskIdRestorePost
    | None
):
    """Restore Task

     Restore a soft-deleted task.

    Args:
        task_id (int):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | RestoreTaskApiV1TasksTaskIdRestorePostResponseRestoreTaskApiV1TasksTaskIdRestorePost
    """

    return sync_detailed(
        task_id=task_id,
        client=client,
    ).parsed


async def asyncio_detailed(
    task_id: int,
    *,
    client: AuthenticatedClient | Client,
) -> Response[
    HTTPValidationError
    | RestoreTaskApiV1TasksTaskIdRestorePostResponseRestoreTaskApiV1TasksTaskIdRestorePost
]:
    """Restore Task

     Restore a soft-deleted task.

    Args:
        task_id (int):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | RestoreTaskApiV1TasksTaskIdRestorePostResponseRestoreTaskApiV1TasksTaskIdRestorePost]
    """

    kwargs = _get_kwargs(
        task_id=task_id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    task_id: int,
    *,
    client: AuthenticatedClient | Client,
) -> (
    HTTPValidationError
    | RestoreTaskApiV1TasksTaskIdRestorePostResponseRestoreTaskApiV1TasksTaskIdRestorePost
    | None
):
    """Restore Task

     Restore a soft-deleted task.

    Args:
        task_id (int):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | RestoreTaskApiV1TasksTaskIdRestorePostResponseRestoreTaskApiV1TasksTaskIdRestorePost
    """

    return (
        await asyncio_detailed(
            task_id=task_id,
            client=client,
        )
    ).parsed
