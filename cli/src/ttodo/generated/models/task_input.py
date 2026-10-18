from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define

from ..models.task_input_priority import TaskInputPriority
from ..models.task_input_status import TaskInputStatus
from ..types import UNSET, Unset

T = TypeVar("T", bound="TaskInput")


@_attrs_define
class TaskInput:
    """Create or partially update task fields.

    Attributes:
        title (str):
        description (None | str | Unset):
        status (TaskInputStatus | Unset):  Default: TaskInputStatus.ASSIGNED.
        priority (TaskInputPriority | Unset):  Default: TaskInputPriority.MEDIUM.
        due_at (datetime.datetime | None | Unset):
        assignees (list[str] | Unset):
        tags (list[str] | Unset):
        labels (list[str] | Unset):
    """

    title: str
    description: str | Unset | None = UNSET
    status: TaskInputStatus | Unset = TaskInputStatus.ASSIGNED
    priority: TaskInputPriority | Unset = TaskInputPriority.MEDIUM
    due_at: datetime.datetime | Unset | None = UNSET
    assignees: list[str] | Unset = UNSET
    tags: list[str] | Unset = UNSET
    labels: list[str] | Unset = UNSET

    def to_dict(self) -> dict[str, Any]:
        title = self.title

        description: str | Unset | None
        if isinstance(self.description, Unset):
            description = UNSET
        else:
            description = self.description

        status: str | Unset = UNSET
        if not isinstance(self.status, Unset):
            status = self.status.value

        priority: str | Unset = UNSET
        if not isinstance(self.priority, Unset):
            priority = self.priority.value

        due_at: str | Unset | None
        if isinstance(self.due_at, Unset):
            due_at = UNSET
        elif isinstance(self.due_at, datetime.datetime):
            due_at = self.due_at.isoformat()
        else:
            due_at = self.due_at

        assignees: list[str] | Unset = UNSET
        if not isinstance(self.assignees, Unset):
            assignees = self.assignees

        tags: list[str] | Unset = UNSET
        if not isinstance(self.tags, Unset):
            tags = self.tags

        labels: list[str] | Unset = UNSET
        if not isinstance(self.labels, Unset):
            labels = self.labels

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "title": title,
            }
        )
        if description is not UNSET:
            field_dict["description"] = description
        if status is not UNSET:
            field_dict["status"] = status
        if priority is not UNSET:
            field_dict["priority"] = priority
        if due_at is not UNSET:
            field_dict["due_at"] = due_at
        if assignees is not UNSET:
            field_dict["assignees"] = assignees
        if tags is not UNSET:
            field_dict["tags"] = tags
        if labels is not UNSET:
            field_dict["labels"] = labels

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        title = d.pop("title")

        def _parse_description(data: object) -> str | Unset | None:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        description = _parse_description(d.pop("description", UNSET))

        _status = d.pop("status", UNSET)
        status: TaskInputStatus | Unset
        if isinstance(_status, Unset):
            status = UNSET
        else:
            status = TaskInputStatus(_status)

        _priority = d.pop("priority", UNSET)
        priority: TaskInputPriority | Unset
        if isinstance(_priority, Unset):
            priority = UNSET
        else:
            priority = TaskInputPriority(_priority)

        def _parse_due_at(data: object) -> datetime.datetime | Unset | None:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                due_at_type_0 = datetime.datetime.fromisoformat(data)

                return due_at_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.datetime | None | Unset, data)

        due_at = _parse_due_at(d.pop("due_at", UNSET))

        assignees = cast(list[str], d.pop("assignees", UNSET))

        tags = cast(list[str], d.pop("tags", UNSET))

        labels = cast(list[str], d.pop("labels", UNSET))

        task_input = cls(
            title=title,
            description=description,
            status=status,
            priority=priority,
            due_at=due_at,
            assignees=assignees,
            tags=tags,
            labels=labels,
        )

        return task_input
