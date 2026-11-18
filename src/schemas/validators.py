"""Shared validators, validator factories, and pure rules for write payloads.

Pure functions only: no Flask globals, no I/O, no schema imports, so every schema
module can depend on this one.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import date, datetime
from typing import Any, Literal


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


def regex_match(
    pattern: re.Pattern[str], copy: str, *, prepare: Callable[[str], str] = lambda s: s
) -> Callable[[Any], str]:
    """Match a prepared string against a pattern; raise ValueError(copy) on mismatch."""

    def validate(value: Any) -> str:
        text = prepare(str(value or ''))
        if not pattern.fullmatch(text):
            raise ValueError(copy)
        return text

    return validate


def integer(copy: str, *, minimum: int | None = None) -> Callable[[Any], int]:
    """Parse int with one copy for bad values and values below minimum."""

    def validate(value: Any) -> int:
        try:
            parsed = int(value)
        except TypeError, ValueError:
            raise ValueError(copy) from None
        if minimum is not None and parsed < minimum:
            raise ValueError(copy)
        return parsed

    return validate


def reject_none(copy: str) -> Callable[[Any], Any]:
    """Reject an explicit null with the caller's copy; absent keys never reach it."""

    def validate(value: Any) -> Any:
        if value is None:
            raise ValueError(copy)
        return value

    return validate


def date_cmp(
    value: date,
    bound: date,
    *,
    op: Literal['lt', 'le', 'eq', 'ne', 'ge', 'gt'],
    copy: str,
) -> None:
    """One date comparison; raise ValueError(copy) when it fails."""
    match op:
        case 'lt':
            ok = value < bound
        case 'le':
            ok = value <= bound
        case 'eq':
            ok = value == bound
        case 'ne':
            ok = value != bound
        case 'ge':
            ok = value >= bound
        case 'gt':
            ok = value > bound
        case _:
            raise RuntimeError(f'Unknown date operator: {op}')
    if not ok:
        raise ValueError(copy)
