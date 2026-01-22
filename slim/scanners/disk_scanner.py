"""Disk usage scanner for development ecosystems."""

import subprocess
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

from slim.core.utils import (
    get_directory_size,
    format_size,
    run_command,
)


@dataclass
class ProjectInfo:
    """Information about a detected project."""
    path: Path
    name: str
    ecosystem: str  # "python", "node", "docker"
    size_bytes: int = 0


@dataclass
class EcosystemUsage:
    """Disk usage for a specific ecosystem."""
    name: str
    total_size: int = 0
    locations: list[tuple[Path, int]] = field(default_factory=list)


@dataclass
class DiskScanResult:
    """Result of scanning disk usage."""
    scan_path: Path
    
    # Ecosystem totals
    python_usage: EcosystemUsage = field(default_factory=lambda: EcosystemUsage(name="Python"))
    node_usage: EcosystemUsage = field(default_factory=lambda: EcosystemUsage(name="Node.js"))
    docker_usage: EcosystemUsage = field(default_factory=lambda: EcosystemUsage(name="Docker"))
    
    # Projects found
    projects: list[ProjectInfo] = field(default_factory=list)
    
    # Errors
    errors: list[str] = field(default_factory=list)


# Common virtual environment directory names
PYTHON_VENV_NAMES = {"venv", ".venv", "env", ".env", "virtualenv", ".virtualenv"}

# Patterns for cache directories
PYTHON_CACHE_PATTERNS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox", ".nox"}


def find_python_environments(root: Path, max_depth: int = 5) -> Iterator[tuple[Path, int]]:
    """Find Python virtual environments and their sizes."""
    
    def search(path: Path, depth: int) -> Iterator[tuple[Path, int]]:
        if depth > max_depth:
            return
        
        try:
            for entry in path.iterdir():
                if not entry.is_dir():
                    continue
                
                # Skip hidden directories (except our target ones)
                if entry.name.startswith(".") and entry.name not in {".venv", ".env", ".virtualenv"}:
                    continue
                
                # Check if this is a virtual environment
                if entry.name in PYTHON_VENV_NAMES:
                    # Verify it's actually a venv by checking for pyvenv.cfg or Scripts/bin
                    is_venv = (
                        (entry / "pyvenv.cfg").exists() or
                        (entry / "Scripts").exists() or
                        (entry / "bin" / "python").exists()
                    )
                    if is_venv:
                        size = get_directory_size(entry)
                        yield (entry, size)
                        continue
                
                # Check for site-packages (indicates a venv we might have missed)
                if entry.name == "lib" or entry.name == "Lib":
                    site_packages = list(entry.rglob("site-packages"))
                    if site_packages:
                        continue  # Parent was likely already caught
                
                # Recurse
                yield from search(entry, depth + 1)
        
        except PermissionError:
            pass
    
    yield from search(root, 0)


def find_node_modules(root: Path, max_depth: int = 5) -> Iterator[tuple[Path, int]]:
    """Find node_modules directories and their sizes."""
    
    def search(path: Path, depth: int) -> Iterator[tuple[Path, int]]:
        if depth > max_depth:
            return
        
        try:
            for entry in path.iterdir():
                if not entry.is_dir():
                    continue
                
                # Skip hidden directories
                if entry.name.startswith("."):
                    continue
                
                if entry.name == "node_modules":
                    size = get_directory_size(entry)
                    yield (entry, size)
                    # Don't recurse into node_modules
                    continue
                
                # Recurse
                yield from search(entry, depth + 1)
        
        except PermissionError:
            pass
    
    yield from search(root, 0)


def get_docker_images() -> list[tuple[str, int]]:
    """Get Docker images and their sizes (read-only)."""
    images: list[tuple[str, int]] = []
    
    # Try to run docker images command
    returncode, stdout, stderr = run_command(
        ["docker", "images", "--format", "{{.Repository}}:{{.Tag}}\t{{.Size}}"]
    )
    
    if returncode != 0:
        return images
    
    for line in stdout.strip().split("\n"):
        if not line or "\t" not in line:
            continue
        
        parts = line.split("\t")
        if len(parts) != 2:
            continue
        
        name, size_str = parts
        
        # Parse size string (e.g., "1.2GB", "500MB", "50KB")
        size_bytes = parse_docker_size(size_str)
        images.append((name, size_bytes))
    
    return images


def parse_docker_size(size_str: str) -> int:
    """Parse Docker size string to bytes."""
    size_str = size_str.strip().upper()
    
    # Match patterns like "1.2GB", "500MB", "50KB", "100B"
    match = re.match(r"([\d.]+)\s*(GB|MB|KB|B)", size_str)
    if not match:
        return 0
    
    value = float(match.group(1))
    unit = match.group(2)
    
    multipliers = {
        "B": 1,
        "KB": 1024,
        "MB": 1024 ** 2,
        "GB": 1024 ** 3,
    }
    
    return int(value * multipliers.get(unit, 1))


def find_projects(root: Path, max_depth: int = 4) -> Iterator[ProjectInfo]:
    """Find all development projects in a directory."""
    
    def search(path: Path, depth: int) -> Iterator[ProjectInfo]:
        if depth > max_depth:
            return
        
        try:
            entries = list(path.iterdir())
            entry_names = {e.name for e in entries}
            
            # Check for Python project
            if "pyproject.toml" in entry_names or "setup.py" in entry_names:
                # Calculate size of Python artifacts
                size = 0
                for venv_name in PYTHON_VENV_NAMES:
                    venv_path = path / venv_name
                    if venv_path.exists():
                        size += get_directory_size(venv_path)
                
                for cache_name in PYTHON_CACHE_PATTERNS:
                    for cache_path in path.rglob(cache_name):
                        if cache_path.is_dir():
                            size += get_directory_size(cache_path)
                
                yield ProjectInfo(
                    path=path,
                    name=path.name,
                    ecosystem="python",
                    size_bytes=size,
                )
            
            # Check for Node.js project
            if "package.json" in entry_names:
                size = 0
                node_modules = path / "node_modules"
                if node_modules.exists():
                    size = get_directory_size(node_modules)
                
                yield ProjectInfo(
                    path=path,
                    name=path.name,
                    ecosystem="node",
                    size_bytes=size,
                )
            
            # Recurse into subdirectories
            for entry in entries:
                if not entry.is_dir():
                    continue
                if entry.name.startswith("."):
                    continue
                if entry.name in {"node_modules", "venv", ".venv", "env", "dist", "build"}:
                    continue
                
                yield from search(entry, depth + 1)
        
        except PermissionError:
            pass
    
    yield from search(root, 0)


def scan_disk(
    scan_path: Path | None = None,
    include_docker: bool = True,
    max_depth: int = 5,
) -> DiskScanResult:
    """
    Scan disk for development ecosystem usage.
    
    Args:
        scan_path: Path to scan. If None, uses current directory.
        include_docker: Whether to include Docker image sizes.
        max_depth: Maximum directory depth to search.
    
    Returns:
        DiskScanResult with all usage information.
    """
    if scan_path is None:
        scan_path = Path.cwd()
    
    result = DiskScanResult(scan_path=scan_path)
    
    # Scan for Python virtual environments
    for path, size in find_python_environments(scan_path, max_depth):
        result.python_usage.locations.append((path, size))
        result.python_usage.total_size += size
    
    # Scan for node_modules
    for path, size in find_node_modules(scan_path, max_depth):
        result.node_usage.locations.append((path, size))
        result.node_usage.total_size += size
    
    # Get Docker images
    if include_docker:
        try:
            docker_images = get_docker_images()
            for name, size in docker_images:
                result.docker_usage.locations.append((Path(name), size))
                result.docker_usage.total_size += size
        except Exception as e:
            result.errors.append(f"Failed to get Docker images: {e}")
    
    # Find projects
    for project in find_projects(scan_path, max_depth):
        result.projects.append(project)
    
    # Sort locations by size (largest first)
    result.python_usage.locations.sort(key=lambda x: x[1], reverse=True)
    result.node_usage.locations.sort(key=lambda x: x[1], reverse=True)
    result.docker_usage.locations.sort(key=lambda x: x[1], reverse=True)
    result.projects.sort(key=lambda x: x.size_bytes, reverse=True)
    
    return result


def get_scan_result_dict(result: DiskScanResult, top_n: int | None = None) -> dict:
    """Convert DiskScanResult to a JSON-serializable dictionary."""
    
    def limit_list(items: list, n: int | None) -> list:
        if n is None:
            return items
        return items[:n]
    
    return {
        "scan_path": str(result.scan_path),
        "ecosystems": {
            "python": {
                "total_size_bytes": result.python_usage.total_size,
                "total_size": format_size(result.python_usage.total_size),
                "locations": [
                    {"path": str(p), "size_bytes": s, "size": format_size(s)}
                    for p, s in limit_list(result.python_usage.locations, top_n)
                ],
            },
            "node": {
                "total_size_bytes": result.node_usage.total_size,
                "total_size": format_size(result.node_usage.total_size),
                "locations": [
                    {"path": str(p), "size_bytes": s, "size": format_size(s)}
                    for p, s in limit_list(result.node_usage.locations, top_n)
                ],
            },
            "docker": {
                "total_size_bytes": result.docker_usage.total_size,
                "total_size": format_size(result.docker_usage.total_size),
                "images": [
                    {"name": str(p), "size_bytes": s, "size": format_size(s)}
                    for p, s in limit_list(result.docker_usage.locations, top_n)
                ],
            },
        },
        "projects": [
            {
                "path": str(p.path),
                "name": p.name,
                "ecosystem": p.ecosystem,
                "size_bytes": p.size_bytes,
                "size": format_size(p.size_bytes),
            }
            for p in limit_list(result.projects, top_n)
        ],
        "errors": result.errors,
    }
