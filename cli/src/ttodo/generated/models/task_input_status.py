from enum import StrEnum


class TaskInputStatus(StrEnum):
    ASSIGNED = "assigned"
    COMPLETED = "completed"
    IN_PROGRESS = "in_progress"

    def __str__(self) -> str:
        return str(self.value)
