import datetime
from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.get_tasks_api_v1_tasks_get_response_get_tasks_api_v1_tasks_get import (
    GetTasksApiV1TasksGetResponseGetTasksApiV1TasksGet,
)
from ...models.http_validation_error import HTTPValidationError
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    status: list[str] | None | Unset = UNSET,
    assignee: None | str | Unset = UNSET,
    priority: None | str | Unset = UNSET,
    due_from: datetime.datetime | None | Unset = UNSET,
    due_to: datetime.datetime | None | Unset = UNSET,
    tag: None | str | Unset = UNSET,
    label: None | str | Unset = UNSET,
    include_completed: bool | Unset = True,
    limit: int | Unset = 20,
    offset: int | Unset = 0,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    json_status: list[str] | Unset | None
    if isinstance(status, Unset):
        json_status = UNSET
    elif isinstance(status, list):
        json_status = status

    else:
        json_status = status
    params["status"] = json_status

    json_assignee: str | Unset | None
    if isinstance(assignee, Unset):
        json_assignee = UNSET
    else:
        json_assignee = assignee
    params["assignee"] = json_assignee

    json_priority: str | Unset | None
    if isinstance(priority, Unset):
        json_priority = UNSET
    else:
        json_priority = priority
    params["priority"] = json_priority

    json_due_from: str | Unset | None
    if isinstance(due_from, Unset):
        json_due_from = UNSET
    elif isinstance(due_from, datetime.datetime):
        json_due_from = due_from.isoformat()
    else:
        json_due_from = due_from
    params["due_from"] = json_due_from

    json_due_to: str | Unset | None
    if isinstance(due_to, Unset):
        json_due_to = UNSET
    elif isinstance(due_to, datetime.datetime):
        json_due_to = due_to.isoformat()
    else:
        json_due_to = due_to
    params["due_to"] = json_due_to

    json_tag: str | Unset | None
    if isinstance(tag, Unset):
        json_tag = UNSET
    else:
        json_tag = tag
    params["tag"] = json_tag

    json_label: str | Unset | None
    if isinstance(label, Unset):
        json_label = UNSET
    else:
        json_label = label
    params["label"] = json_label

    params["include_completed"] = include_completed

    params["limit"] = limit

    params["offset"] = offset

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/tasks",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> GetTasksApiV1TasksGetResponseGetTasksApiV1TasksGet | HTTPValidationError | None:
    if response.status_code == 200:
        response_200 = GetTasksApiV1TasksGetResponseGetTasksApiV1TasksGet.from_dict(
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
) -> Response[GetTasksApiV1TasksGetResponseGetTasksApiV1TasksGet | HTTPValidationError]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    status: list[str] | None | Unset = UNSET,
    assignee: None | str | Unset = UNSET,
    priority: None | str | Unset = UNSET,
    due_from: datetime.datetime | None | Unset = UNSET,
    due_to: datetime.datetime | None | Unset = UNSET,
    tag: None | str | Unset = UNSET,
    label: None | str | Unset = UNSET,
    include_completed: bool | Unset = True,
    limit: int | Unset = 20,
    offset: int | Unset = 0,
) -> Response[GetTasksApiV1TasksGetResponseGetTasksApiV1TasksGet | HTTPValidationError]:
    """Get Tasks

     List active tasks matching every supplied filter.

    Args:
        status (list[str] | None | Unset):
        assignee (None | str | Unset):
        priority (None | str | Unset):
        due_from (datetime.datetime | None | Unset):
        due_to (datetime.datetime | None | Unset):
        tag (None | str | Unset):
        label (None | str | Unset):
        include_completed (bool | Unset):  Default: True.
        limit (int | Unset):  Default: 20.
        offset (int | Unset):  Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[GetTasksApiV1TasksGetResponseGetTasksApiV1TasksGet | HTTPValidationError]
    """

    kwargs = _get_kwargs(
        status=status,
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

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
    status: list[str] | None | Unset = UNSET,
    assignee: None | str | Unset = UNSET,
    priority: None | str | Unset = UNSET,
    due_from: datetime.datetime | None | Unset = UNSET,
    due_to: datetime.datetime | None | Unset = UNSET,
    tag: None | str | Unset = UNSET,
    label: None | str | Unset = UNSET,
    include_completed: bool | Unset = True,
    limit: int | Unset = 20,
    offset: int | Unset = 0,
) -> GetTasksApiV1TasksGetResponseGetTasksApiV1TasksGet | HTTPValidationError | None:
    """Get Tasks

     List active tasks matching every supplied filter.

    Args:
        status (list[str] | None | Unset):
        assignee (None | str | Unset):
        priority (None | str | Unset):
        due_from (datetime.datetime | None | Unset):
        due_to (datetime.datetime | None | Unset):
        tag (None | str | Unset):
        label (None | str | Unset):
        include_completed (bool | Unset):  Default: True.
        limit (int | Unset):  Default: 20.
        offset (int | Unset):  Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        GetTasksApiV1TasksGetResponseGetTasksApiV1TasksGet | HTTPValidationError
    """

    return sync_detailed(
        client=client,
        status=status,
        assignee=assignee,
        priority=priority,
        due_from=due_from,
        due_to=due_to,
        tag=tag,
        label=label,
        include_completed=include_completed,
        limit=limit,
        offset=offset,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    status: list[str] | None | Unset = UNSET,
    assignee: None | str | Unset = UNSET,
    priority: None | str | Unset = UNSET,
    due_from: datetime.datetime | None | Unset = UNSET,
    due_to: datetime.datetime | None | Unset = UNSET,
    tag: None | str | Unset = UNSET,
    label: None | str | Unset = UNSET,
    include_completed: bool | Unset = True,
    limit: int | Unset = 20,
    offset: int | Unset = 0,
) -> Response[GetTasksApiV1TasksGetResponseGetTasksApiV1TasksGet | HTTPValidationError]:
    """Get Tasks

     List active tasks matching every supplied filter.

    Args:
        status (list[str] | None | Unset):
        assignee (None | str | Unset):
        priority (None | str | Unset):
        due_from (datetime.datetime | None | Unset):
        due_to (datetime.datetime | None | Unset):
        tag (None | str | Unset):
        label (None | str | Unset):
        include_completed (bool | Unset):  Default: True.
        limit (int | Unset):  Default: 20.
        offset (int | Unset):  Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[GetTasksApiV1TasksGetResponseGetTasksApiV1TasksGet | HTTPValidationError]
    """

    kwargs = _get_kwargs(
        status=status,
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

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    status: list[str] | None | Unset = UNSET,
    assignee: None | str | Unset = UNSET,
    priority: None | str | Unset = UNSET,
    due_from: datetime.datetime | None | Unset = UNSET,
    due_to: datetime.datetime | None | Unset = UNSET,
    tag: None | str | Unset = UNSET,
    label: None | str | Unset = UNSET,
    include_completed: bool | Unset = True,
    limit: int | Unset = 20,
    offset: int | Unset = 0,
) -> GetTasksApiV1TasksGetResponseGetTasksApiV1TasksGet | HTTPValidationError | None:
    """Get Tasks

     List active tasks matching every supplied filter.

    Args:
        status (list[str] | None | Unset):
        assignee (None | str | Unset):
        priority (None | str | Unset):
        due_from (datetime.datetime | None | Unset):
        due_to (datetime.datetime | None | Unset):
        tag (None | str | Unset):
        label (None | str | Unset):
        include_completed (bool | Unset):  Default: True.
        limit (int | Unset):  Default: 20.
        offset (int | Unset):  Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        GetTasksApiV1TasksGetResponseGetTasksApiV1TasksGet | HTTPValidationError
    """

    return (
        await asyncio_detailed(
            client=client,
            status=status,
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
    ).parsed
