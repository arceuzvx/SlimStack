"""
Cache cleanup scanner and cleaner for SlimStack.

Finds and optionally removes common development cache directories:
- Python: __pycache__, .pytest_cache, .mypy_cache, .ruff_cache, .tox, *.pyc
- Node.js: node_modules/.cache, .next, .nuxt, dist, build
- General: .cache, .parcel-cache, .turbo
"""

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

from slim.core.config import SKIP_DIRECTORIES


# Cache directory patterns by ecosystem
PYTHON_CACHE_DIRS = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".coverage",
    ".eggs",
    "*.egg-info",
    ".pytype",
    ".pyre",
}

NODE_CACHE_DIRS = {
    ".next",
    ".nuxt",
    ".parcel-cache",
    ".turbo",
}

# Directories that are caches ONLY inside node_modules
NODE_INTERNAL_CACHE = "node_modules/.cache"

GENERAL_CACHE_DIRS = {
    ".cache",
}

# Build output directories (only cleaned with --include-builds)
BUILD_DIRS = {
    "dist",
    "build",
    "out",
}

ALL_CACHE_NAMES = PYTHON_CACHE_DIRS | NODE_CACHE_DIRS | GENERAL_CACHE_DIRS


@dataclass
class CacheEntry:
    """A single cache directory found on disk."""
    path: Path
    size: int
    category: str  # "python", "node", "general", "build"
    name: str      # directory name


@dataclass
class CleanResult:
    """Result of scanning for cache directories."""
    scan_path: Path
    entries: list[CacheEntry] = field(default_factory=list)
    total_size: int = 0
    cleaned_count: int = 0
    cleaned_size: int = 0
    errors: list[str] = field(default_factory=list)


def _get_dir_size(path: Path) -> int:
    """Calculate total size of a directory."""
    total = 0
    try:
        for item in path.rglob("*"):
            if item.is_file():
                try:
                    total += item.stat().st_size
                except OSError:
                    pass
    except (PermissionError, OSError):
        pass
    return total


def _categorize(name: str) -> str:
    """Determine the ecosystem category for a cache directory name."""
    if name in PYTHON_CACHE_DIRS or name.endswith(".egg-info"):
        return "python"
    if name in NODE_CACHE_DIRS or name == ".cache":
        return "node"
    if name in BUILD_DIRS:
        return "build"
    return "general"


def scan_caches(
    scan_path: Path | None = None,
    include_builds: bool = False,
    max_depth: int = 6,
) -> CleanResult:
    """
    Scan for cache directories starting from scan_path.
    
    Args:
        scan_path: Root path to scan (default: cwd)
        include_builds: Also include dist/build/out directories
        max_depth: Maximum directory depth to recurse
    
    Returns:
        CleanResult with all found cache entries
    """
    if scan_path is None:
        scan_path = Path.cwd()
    
    result = CleanResult(scan_path=scan_path.resolve())
    target_names = ALL_CACHE_NAMES.copy()
    if include_builds:
        target_names |= BUILD_DIRS
    
    seen: set[Path] = set()
    
    def walk(path: Path, depth: int) -> None:
        if depth > max_depth:
            return
        
        try:
            entries = sorted(path.iterdir())
        except (PermissionError, OSError):
            return
        
        for entry in entries:
            if not entry.is_dir():
                continue
            
            name = entry.name
            resolved = entry.resolve()
            
            if resolved in seen:
                continue
            
            # Skip venvs and node_modules themselves (disk scanner handles those)
            if name in {"venv", ".venv", "env", ".env", "node_modules", ".git"}:
                # But check for node_modules/.cache
                if name == "node_modules":
                    cache_inside = entry / ".cache"
                    if cache_inside.is_dir() and cache_inside.resolve() not in seen:
                        seen.add(cache_inside.resolve())
                        size = _get_dir_size(cache_inside)
                        result.entries.append(CacheEntry(
                            path=cache_inside,
                            size=size,
                            category="node",
                            name="node_modules/.cache",
                        ))
                        result.total_size += size
                continue
            
            # Check if this is a cache directory
            matched = False
            if name in target_names:
                matched = True
            elif name.endswith(".egg-info") and not include_builds:
                matched = "*.egg-info" in target_names
            elif name.endswith(".egg-info") and include_builds:
                matched = True
            
            if matched:
                seen.add(resolved)
                size = _get_dir_size(entry)
                result.entries.append(CacheEntry(
                    path=entry,
                    size=size,
                    category=_categorize(name),
                    name=name,
                ))
                result.total_size += size
                continue  # Don't recurse into cache dirs
            
            # Recurse into non-cache directories
            if not name.startswith("."):
                walk(entry, depth + 1)
    
    walk(scan_path.resolve(), 0)
    
    # Sort by size descending
    result.entries.sort(key=lambda e: e.size, reverse=True)
    
    return result


def clean_caches(result: CleanResult, entries_to_clean: list[CacheEntry] | None = None) -> CleanResult:
    """
    Delete the specified cache directories.
    
    Args:
        result: A CleanResult from scan_caches
        entries_to_clean: Specific entries to clean (default: all)
    
    Returns:
        Updated CleanResult with cleaned counts
    """
    targets = entries_to_clean if entries_to_clean is not None else result.entries
    
    for entry in targets:
        try:
            shutil.rmtree(entry.path)
            result.cleaned_count += 1
            result.cleaned_size += entry.size
        except (PermissionError, OSError) as e:
            result.errors.append(f"Failed to remove {entry.path}: {e}")
    
    return result


def get_clean_result_dict(result: CleanResult) -> dict:
    """Convert CleanResult to JSON-serializable dictionary."""
    return {
        "scan_path": str(result.scan_path),
        "total_size": result.total_size,
        "entries": [
            {
                "path": str(e.path),
                "size": e.size,
                "category": e.category,
                "name": e.name,
            }
            for e in result.entries
        ],
        "cleaned_count": result.cleaned_count,
        "cleaned_size": result.cleaned_size,
        "errors": result.errors,
        "summary": {
            "total_entries": len(result.entries),
            "by_category": _count_by_category(result),
        },
    }


def _count_by_category(result: CleanResult) -> dict[str, dict]:
    """Summarize entries by category."""
    cats: dict[str, dict] = {}
    for entry in result.entries:
        if entry.category not in cats:
            cats[entry.category] = {"count": 0, "size": 0}
        cats[entry.category]["count"] += 1
        cats[entry.category]["size"] += entry.size
    return cats
