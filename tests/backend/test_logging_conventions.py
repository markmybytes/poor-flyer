"""Guard the log message convention from STYLE.md: lowercase event, one event, no period.

Only shapes that are certainly wrong are flagged. An all-caps word may open a
message (``API token expired``), other non-literal arguments are left alone, and
a sentence break only counts when a full stop is followed by a capital letter.
"""

import ast
import re
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2] / 'src'
LEVELS = {'debug', 'info', 'warning', 'warn', 'error', 'exception', 'critical'}
ACRONYM_OPEN = re.compile(r'^[A-Z][A-Z0-9]{1,}\b')
SENTENCE_BREAK = re.compile(r'\.\s+[A-Z]')
LOGGING_OWNER = 'src/logging_config.py'
OWNED_CALLS = {'addHandler', 'setLevel', 'basicConfig', 'dictConfig'}


def _log_messages() -> list[tuple[str, int, ast.expr]]:
    found = []
    for path in sorted(SRC.rglob('*.py')):
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not isinstance(func, ast.Attribute) or func.attr not in LEVELS:
                continue
            owner = func.value
            name = owner.id if isinstance(owner, ast.Name) else getattr(owner, 'attr', '')
            if name != 'logger' or not node.args:
                continue
            found.append((str(path.relative_to(SRC.parent)), node.lineno, node.args[0]))
    return found


def _violation(path: str, line: int, arg: ast.expr) -> str | None:
    where = f'{path}:{line}'
    if isinstance(arg, ast.JoinedStr):
        return f'{where}: message is an f-string'
    if not (isinstance(arg, ast.Constant) and isinstance(arg.value, str)):
        return None  # a variable holds the text; only ruff can judge that
    message = arg.value
    if message.endswith('.'):
        return f'{where}: ends with a period: {message!r}'
    if SENTENCE_BREAK.search(message):
        return f'{where}: second sentence: {message!r}'
    if '\n' in message:
        return f'{where}: spans lines: {message!r}'
    if message[:1].isupper() and not ACRONYM_OPEN.match(message):
        return f'{where}: starts uppercase: {message!r}'
    return None


def test_log_messages_follow_the_convention():
    calls = _log_messages()
    assert len(calls) > 50, 'convention guard found no logger calls to check'

    problems = [
        violation
        for path, line, arg in calls
        if (violation := _violation(path, line, arg)) is not None
    ]
    assert not problems, 'log message convention violations:\n' + '\n'.join(problems)


@pytest.mark.parametrize(
    'source',
    [
        "'Scraped prices'",
        "'scraped prices.'",
        "'scrape failed. Retrying later'",
        "'scrape\\nfailed'",
        'f"scraped {count} prices"',
    ],
)
def test_violation_flags_bad_shapes(source):
    arg = ast.parse(source, mode='eval').body
    assert _violation('src/demo.py', 1, arg) is not None


@pytest.mark.parametrize(
    'source',
    [
        "'scraped prices: count=%d'",
        "'loaded FX cache: base=%s entries=%d'",
        "'API token expired'",
        "'no fx rate for conversion: src=%s tgt=%s'",
        "'retry in 1.5s'",
        'message',
    ],
)
def test_violation_accepts_good_shapes(source):
    arg = ast.parse(source, mode='eval').body
    assert _violation('src/demo.py', 1, arg) is None


def _logging_ownership_violations() -> list[str]:
    problems = []
    for path in sorted(SRC.rglob('*.py')):
        relative = str(path.relative_to(SRC.parent)).replace('\\', '/')
        if relative == LOGGING_OWNER:
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in OWNED_CALLS:
                    problems.append(f'{relative}:{node.lineno}: {node.func.attr}()')
    return problems


def test_only_logging_config_owns_handlers_and_levels():
    assert (SRC / 'logging_config.py').exists(), 'logging guard lost its reference module'
    problems = _logging_ownership_violations()
    assert not problems, 'handler and level calls belong in src/logging_config.py:\n' + '\n'.join(
        problems
    )
