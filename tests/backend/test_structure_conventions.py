"""Guard the STYLE.md placement rule that review alone cannot enforce.

Routes are built through blueprints, never on the app object.
"""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'src'

# Blueprint registration belongs in the factory or in a blueprint package __init__.
REGISTRATION_SITES = {
    'src/__init__.py',
    *{
        f'src/routes/{package.name}/__init__.py'
        for package in (SRC / 'routes').iterdir()
        if package.is_dir()
    },
}


def _relative(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace('\\', '/')


def _python_files(directory: Path) -> list[Path]:
    return sorted(directory.rglob('*.py'))


def _call_violation(relative: str, node: ast.Call) -> str | None:
    if not isinstance(node.func, ast.Attribute):
        return None
    owner = node.func.value
    owner_name = owner.id if isinstance(owner, ast.Name) else ''
    if node.func.attr == 'add_url_rule' and owner_name == 'app':
        return f'{relative}:{node.lineno}: app.add_url_rule()'
    if node.func.attr == 'register_blueprint' and relative not in REGISTRATION_SITES:
        return f'{relative}:{node.lineno}: register_blueprint()'
    return None


def _decorator_violation(relative: str, node: ast.FunctionDef) -> str | None:
    for decorator in node.decorator_list:
        if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
            continue
        owner = decorator.func.value
        if decorator.func.attr == 'route' and isinstance(owner, ast.Name) and owner.id == 'app':
            return f'{relative}:{node.lineno}: @app.route()'
    return None


def _route_registrations() -> list[str]:
    problems = []
    for path in _python_files(SRC):
        relative = _relative(path)
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
            if isinstance(node, ast.Call):
                problem = _call_violation(relative, node)
            elif isinstance(node, ast.FunctionDef):
                problem = _decorator_violation(relative, node)
            else:
                continue
            if problem:
                problems.append(problem)
    return problems


def test_routes_are_built_through_blueprints():
    problems = _route_registrations()
    assert not problems, 'register routes on a blueprint, not on the app:\n' + '\n'.join(problems)
