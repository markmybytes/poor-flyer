"""Domain errors that carry their form field to the transport layer."""

from __future__ import annotations

from typing import NamedTuple


class FieldIssue(NamedTuple):
    """One failing form field and the user-facing copy the view writes under it."""

    field: str
    message: str


class InvalidFieldsError(ValueError):
    """Every failing field of one submission, raised together so nothing masks a sibling."""

    def __init__(self, errors: list[FieldIssue]) -> None:
        super().__init__('; '.join(issue.message for issue in errors))
        self.errors = errors
