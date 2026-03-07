"""
Configuration file loader for SlimStack.

Supports .slimrc.toml in the project root or user home directory.
Uses Python 3.11+ tomllib (stdlib) for zero-dependency TOML parsing.
"""

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


CONFIG_FILENAMES = [".slimrc.toml", "slimstack.toml"]


@dataclass
class SlimConfig:
    """Parsed SlimStack configuration."""

    # Packages to exclude from "unused" reports
    exclude_packages: list[str] = field(default_factory=list)

    # Default CLI flags
    default_json: bool = False
    default_verbose: bool = False
    default_quiet: bool = False

    # Scan options
    scan_exclude_dirs: list[str] = field(default_factory=list)
    scan_exclude_files: list[str] = field(default_factory=list)

    # Python-specific
    python_exclude: list[str] = field(default_factory=list)
    python_known_mappings: dict[str, str] = field(default_factory=dict)

    # Node-specific
    node_exclude: list[str] = field(default_factory=list)
    node_include_dev: bool = False

    # Docker-specific
    docker_severity: str | None = None
    docker_security_only: bool = False

    # CI options
    fail_on_unused: bool = False

    # Source file path (for diagnostics)
    config_path: Path | None = None


def _find_config_file(start_path: Path | None = None) -> Path | None:
    """
    Search for a config file starting from start_path and walking up to root,
    then checking the user's home directory.
    """
    if start_path is None:
        start_path = Path.cwd()

    current = start_path.resolve()

    # Walk up directory tree
    while True:
        for name in CONFIG_FILENAMES:
            candidate = current / name
            if candidate.is_file():
                return candidate
        parent = current.parent
        if parent == current:
            break
        current = parent

    # Check user home directory
    home = Path.home()
    for name in CONFIG_FILENAMES:
        candidate = home / name
        if candidate.is_file():
            return candidate

    return None


def _parse_toml(path: Path) -> dict[str, Any]:
    """Parse a TOML file and return its contents as a dict."""
    if tomllib is None:
        return {}

    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except Exception:
        return {}


def _merge_config(data: dict[str, Any], config: SlimConfig) -> SlimConfig:
    """Merge parsed TOML data into a SlimConfig instance."""

    # Top-level options
    if "exclude" in data:
        exclude = data["exclude"]
        if isinstance(exclude, list):
            config.exclude_packages = [str(p) for p in exclude]

    if "fail_on_unused" in data:
        config.fail_on_unused = bool(data["fail_on_unused"])

    # [defaults] section
    defaults = data.get("defaults", {})
    if isinstance(defaults, dict):
        if "json" in defaults:
            config.default_json = bool(defaults["json"])
        if "verbose" in defaults:
            config.default_verbose = bool(defaults["verbose"])
        if "quiet" in defaults:
            config.default_quiet = bool(defaults["quiet"])

    # [scan] section
    scan = data.get("scan", {})
    if isinstance(scan, dict):
        if "exclude_dirs" in scan:
            dirs = scan["exclude_dirs"]
            if isinstance(dirs, list):
                config.scan_exclude_dirs = [str(d) for d in dirs]
        if "exclude_files" in scan:
            files = scan["exclude_files"]
            if isinstance(files, list):
                config.scan_exclude_files = [str(f) for f in files]

    # [python] section
    python = data.get("python", {})
    if isinstance(python, dict):
        if "exclude" in python:
            excl = python["exclude"]
            if isinstance(excl, list):
                config.python_exclude = [str(p) for p in excl]
        if "known_mappings" in python:
            mappings = python["known_mappings"]
            if isinstance(mappings, dict):
                config.python_known_mappings = {
                    str(k): str(v) for k, v in mappings.items()
                }

    # [node] section
    node = data.get("node", {})
    if isinstance(node, dict):
        if "exclude" in node:
            excl = node["exclude"]
            if isinstance(excl, list):
                config.node_exclude = [str(p) for p in excl]
        if "include_dev" in node:
            config.node_include_dev = bool(node["include_dev"])

    # [docker] section
    docker = data.get("docker", {})
    if isinstance(docker, dict):
        if "severity" in docker:
            config.docker_severity = str(docker["severity"])
        if "security_only" in docker:
            config.docker_security_only = bool(docker["security_only"])

    return config


def load_config(start_path: Path | None = None) -> SlimConfig:
    """
    Load SlimStack configuration from the nearest config file.

    Searches upward from start_path (default: cwd), then falls back to
    the user's home directory. Returns a default config if no file is found.
    """
    config = SlimConfig()

    config_path = _find_config_file(start_path)
    if config_path is None:
        return config

    config.config_path = config_path
    data = _parse_toml(config_path)
    if data:
        _merge_config(data, config)

    return config
