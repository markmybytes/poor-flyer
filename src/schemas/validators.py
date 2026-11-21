"""Reusable pydantic validators and factories shared by the write-payload schemas.

Pure functions only: no Flask globals, no I/O, no schema imports, so every schema
module can depend on this one.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime
from typing import Any


def iso_date(copy: str, *, allow_empty: bool = False) -> Callable[[Any], date | None]:
    """Lenient YYYY-MM-DD parse; when allow_empty, None/'' clear the field."""

    def validate(value: Any) -> date | None:
        if allow_empty and value in (None, ''):
            return None
        try:
            return datetime.strptime(str(value), '%Y-%m-%d').date()
        except ValueError:
            raise ValueError(copy) from None

    return validate


def reject_none(copy: str) -> Callable[[Any], Any]:
    """Reject an explicit null with the caller's copy; absent keys never reach it."""

    def validate(value: Any) -> Any:
        if value is None:
            raise ValueError(copy)
        return value

    return validate
