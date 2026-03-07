"""
Parser for declared Python dependencies.

Reads requirements.txt and pyproject.toml to determine which packages
are declared (not just installed), enabling detection of:
- Declared but not installed
- Installed but not declared
"""

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ImportError:
        tomllib = None  # type: ignore[assignment]

from slim.scanners.python_scanner import normalize_package_name


@dataclass
class DeclaredDeps:
    """Parsed declared dependencies from project files."""
    source_file: Path | None = None
    dependencies: dict[str, str] = field(default_factory=dict)  # name -> version_spec
    dev_dependencies: dict[str, str] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


# Regex for requirements.txt lines
_REQ_LINE = re.compile(
    r"""
    ^
    (?P<name>[A-Za-z0-9]([A-Za-z0-9._-]*[A-Za-z0-9])?)
    \s*
    (?P<spec>[><=!~]+\s*[\d.*]+(?:\s*,\s*[><=!~]+\s*[\d.*]+)*)?
    """,
    re.VERBOSE,
)


def parse_requirements_txt(path: Path) -> DeclaredDeps:
    """Parse a requirements.txt file."""
    result = DeclaredDeps(source_file=path)

    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        result.errors.append(f"Failed to read {path}: {e}")
        return result

    for line in content.splitlines():
        line = line.strip()

        # Skip comments, empty lines, options, includes
        if not line or line.startswith("#") or line.startswith("-"):
            continue

        match = _REQ_LINE.match(line)
        if match:
            name = match.group("name")
            spec = match.group("spec") or ""
            normalized = normalize_package_name(name)
            result.dependencies[normalized] = spec.strip()

    return result


def parse_pyproject_toml(path: Path) -> DeclaredDeps:
    """Parse dependencies from a pyproject.toml file."""
    result = DeclaredDeps(source_file=path)

    if tomllib is None:
        result.errors.append("tomllib not available (requires Python 3.11+)")
        return result

    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except Exception as e:
        result.errors.append(f"Failed to parse {path}: {e}")
        return result

    # PEP 621: [project] dependencies
    project = data.get("project", {})
    if isinstance(project, dict):
        deps = project.get("dependencies", [])
        if isinstance(deps, list):
            for dep in deps:
                _parse_dep_string(str(dep), result.dependencies)

        # Optional dependencies (dev, test, etc.)
        optional = project.get("optional-dependencies", {})
        if isinstance(optional, dict):
            for group_name, group_deps in optional.items():
                if isinstance(group_deps, list):
                    for dep in group_deps:
                        _parse_dep_string(str(dep), result.dev_dependencies)

    # Poetry: [tool.poetry.dependencies]
    poetry = data.get("tool", {}).get("poetry", {})
    if isinstance(poetry, dict):
        for name, version in poetry.get("dependencies", {}).items():
            if name.lower() == "python":
                continue
            normalized = normalize_package_name(name)
            if isinstance(version, str):
                result.dependencies[normalized] = version
            elif isinstance(version, dict):
                result.dependencies[normalized] = version.get("version", "")

        for name, version in poetry.get("dev-dependencies", {}).items():
            normalized = normalize_package_name(name)
            if isinstance(version, str):
                result.dev_dependencies[normalized] = version

    return result


def _parse_dep_string(dep_str: str, target: dict[str, str]) -> None:
    """Parse a PEP 508 dependency string like 'requests>=2.0'."""
    match = _REQ_LINE.match(dep_str.strip())
    if match:
        name = match.group("name")
        spec = match.group("spec") or ""
        normalized = normalize_package_name(name)
        target[normalized] = spec.strip()


def find_and_parse_declared_deps(project_path: Path) -> DeclaredDeps | None:
    """
    Find and parse declared dependencies from a Python project.

    Searches for (in order): requirements.txt, pyproject.toml, setup.cfg.
    Returns None if no dependency file is found.
    """
    # Try requirements.txt first
    req_txt = project_path / "requirements.txt"
    if req_txt.is_file():
        return parse_requirements_txt(req_txt)

    # Try pyproject.toml
    pyproject = project_path / "pyproject.toml"
    if pyproject.is_file():
        return parse_pyproject_toml(pyproject)

    return None
