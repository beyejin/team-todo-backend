from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define

from ..models.task_patch_priority_type_0 import TaskPatchPriorityType0
from ..models.task_patch_status_type_0 import TaskPatchStatusType0
from ..types import UNSET, Unset

T = TypeVar("T", bound="TaskPatch")


@_attrs_define
class TaskPatch:
    """Fields accepted by a partial task update.

    Attributes:
        title (None | str | Unset):
        description (None | str | Unset):
        status (None | TaskPatchStatusType0 | Unset):
        priority (None | TaskPatchPriorityType0 | Unset):
        due_at (datetime.datetime | None | Unset):
        assignees (list[str] | None | Unset):
        tags (list[str] | None | Unset):
        labels (list[str] | None | Unset):
    """

    title: str | Unset | None = UNSET
    description: str | Unset | None = UNSET
    status: TaskPatchStatusType0 | Unset | None = UNSET
    priority: TaskPatchPriorityType0 | Unset | None = UNSET
    due_at: datetime.datetime | Unset | None = UNSET
    assignees: list[str] | Unset | None = UNSET
    tags: list[str] | Unset | None = UNSET
    labels: list[str] | Unset | None = UNSET

    def to_dict(self) -> dict[str, Any]:
        title: str | Unset | None
        if isinstance(self.title, Unset):
            title = UNSET
        else:
            title = self.title

        description: str | Unset | None
        if isinstance(self.description, Unset):
            description = UNSET
        else:
            description = self.description

        status: str | Unset | None
        if isinstance(self.status, Unset):
            status = UNSET
        elif isinstance(self.status, TaskPatchStatusType0):
            status = self.status.value
        else:
            status = self.status

        priority: str | Unset | None
        if isinstance(self.priority, Unset):
            priority = UNSET
        elif isinstance(self.priority, TaskPatchPriorityType0):
            priority = self.priority.value
        else:
            priority = self.priority

        due_at: str | Unset | None
        if isinstance(self.due_at, Unset):
            due_at = UNSET
        elif isinstance(self.due_at, datetime.datetime):
            due_at = self.due_at.isoformat()
        else:
            due_at = self.due_at

        assignees: list[str] | Unset | None
        if isinstance(self.assignees, Unset):
            assignees = UNSET
        elif isinstance(self.assignees, list):
            assignees = self.assignees

        else:
            assignees = self.assignees

        tags: list[str] | Unset | None
        if isinstance(self.tags, Unset):
            tags = UNSET
        elif isinstance(self.tags, list):
            tags = self.tags

        else:
            tags = self.tags

        labels: list[str] | Unset | None
        if isinstance(self.labels, Unset):
            labels = UNSET
        elif isinstance(self.labels, list):
            labels = self.labels

        else:
            labels = self.labels

        field_dict: dict[str, Any] = {}

        field_dict.update({})
        if title is not UNSET:
            field_dict["title"] = title
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

        def _parse_title(data: object) -> str | Unset | None:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        title = _parse_title(d.pop("title", UNSET))

        def _parse_description(data: object) -> str | Unset | None:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        description = _parse_description(d.pop("description", UNSET))

        def _parse_status(data: object) -> TaskPatchStatusType0 | Unset | None:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                status_type_0 = TaskPatchStatusType0(data)

                return status_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | TaskPatchStatusType0 | Unset, data)

        status = _parse_status(d.pop("status", UNSET))

        def _parse_priority(data: object) -> TaskPatchPriorityType0 | Unset | None:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                priority_type_0 = TaskPatchPriorityType0(data)

                return priority_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | TaskPatchPriorityType0 | Unset, data)

        priority = _parse_priority(d.pop("priority", UNSET))

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

        def _parse_assignees(data: object) -> list[str] | Unset | None:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                assignees_type_0 = cast(list[str], data)

                return assignees_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[str] | None | Unset, data)

        assignees = _parse_assignees(d.pop("assignees", UNSET))

        def _parse_tags(data: object) -> list[str] | Unset | None:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                tags_type_0 = cast(list[str], data)

                return tags_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[str] | None | Unset, data)

        tags = _parse_tags(d.pop("tags", UNSET))

        def _parse_labels(data: object) -> list[str] | Unset | None:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                labels_type_0 = cast(list[str], data)

                return labels_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[str] | None | Unset, data)

        labels = _parse_labels(d.pop("labels", UNSET))

        task_patch = cls(
            title=title,
            description=description,
            status=status,
            priority=priority,
            due_at=due_at,
            assignees=assignees,
            tags=tags,
            labels=labels,
        )

        return task_patch
