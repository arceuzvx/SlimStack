"""Shared utility functions for SlimStack."""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Any


def is_in_virtualenv() -> bool:
    """Check if we're running inside a virtual environment."""
    return (
        hasattr(sys, 'real_prefix') or  # virtualenv
        (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)  # venv
    )


def get_virtualenv_path() -> Path | None:
    """Get the path to the current virtual environment, if any."""
    if is_in_virtualenv():
        return Path(sys.prefix)
    return None


def format_size(size_bytes: int) -> str:
    """Format byte size into human-readable string."""
    if size_bytes < 0:
        return "0 B"
    
    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0
    size = float(size_bytes)
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    return f"{size:.1f} {units[unit_index]}"


def get_directory_size(path: Path) -> int:
    """Calculate total size of a directory in bytes."""
    total = 0
    try:
        for entry in path.rglob("*"):
            if entry.is_file():
                try:
                    total += entry.stat().st_size
                except (OSError, PermissionError):
                    pass
    except (OSError, PermissionError):
        pass
    return total


def run_command(cmd: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    """
    Run a command and return (returncode, stdout, stderr).
    
    Args:
        cmd: Command and arguments as a list
        cwd: Working directory for the command
    
    Returns:
        Tuple of (return_code, stdout, stderr)
    """
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=60,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except FileNotFoundError:
        return -1, "", f"Command not found: {cmd[0]}"
    except Exception as e:
        return -1, "", str(e)


def find_project_root(start_path: Path | None = None) -> Path:
    """
    Find the project root by looking for common project markers.
    
    Looks for: pyproject.toml, setup.py, package.json, .git
    """
    if start_path is None:
        start_path = Path.cwd()
    
    current = start_path.resolve()
    markers = {"pyproject.toml", "setup.py", "setup.cfg", "package.json", ".git"}
    
    while current != current.parent:
        for marker in markers:
            if (current / marker).exists():
                return current
        current = current.parent
    
    # No marker found, return original path
    return start_path.resolve()


def confirm_action(message: str) -> bool:
    """
    Prompt user for confirmation.
    
    Returns True if user confirms, False otherwise.
    """
    try:
        response = input(f"{message} [y/N]: ").strip().lower()
        return response in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        print()  # Newline after ^C
        return False


def output_json(data: Any) -> None:
    """Output data as formatted JSON to stdout."""
    print(json.dumps(data, indent=2, default=str))


def is_tty() -> bool:
    """Check if stdout is connected to a TTY."""
    return hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()


def error(message: str) -> None:
    """Print an error message to stderr."""
    from slim.core.config import Colors
    if is_tty():
        print(f"{Colors.RED}Error:{Colors.RESET} {message}", file=sys.stderr)
    else:
        print(f"Error: {message}", file=sys.stderr)


def warn(message: str) -> None:
    """Print a warning message to stderr."""
    from slim.core.config import Colors
    if is_tty():
        print(f"{Colors.YELLOW}Warning:{Colors.RESET} {message}", file=sys.stderr)
    else:
        print(f"Warning: {message}", file=sys.stderr)


def info(message: str) -> None:
    """Print an info message."""
    from slim.core.config import Colors
    if is_tty():
        print(f"{Colors.CYAN}→{Colors.RESET} {message}")
    else:
        print(f"→ {message}")


def success(message: str) -> None:
    """Print a success message."""
    from slim.core.config import Colors
    if is_tty():
        print(f"{Colors.GREEN}✓{Colors.RESET} {message}")
    else:
        print(f"✓ {message}")
