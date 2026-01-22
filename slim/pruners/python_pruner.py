"""Python package pruner with safety guards."""

import sys
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from slim.core.config import PYTHON_PROTECTED_PACKAGES, Colors
from slim.core.utils import (
    is_in_virtualenv,
    confirm_action,
    format_size,
    error,
    warn,
    info,
    success,
    is_tty,
)
from slim.scanners.python_scanner import scan_python_project, ScanResult


@dataclass
class PruneResult:
    """Result of a prune operation."""
    packages_removed: list[str] = field(default_factory=list)
    packages_failed: list[tuple[str, str]] = field(default_factory=list)
    bytes_freed: int = 0
    dry_run: bool = True
    errors: list[str] = field(default_factory=list)


def get_package_size(package_name: str) -> int:
    """Estimate the size of an installed package."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "show", "-f", package_name],
            capture_output=True,
            text=True,
            timeout=10,
        )
        
        if result.returncode != 0:
            return 0
        
        # Parse location
        location = None
        for line in result.stdout.split("\n"):
            if line.startswith("Location:"):
                location = line.split(":", 1)[1].strip()
                break
        
        if not location:
            return 0
        
        # Parse files and calculate size
        in_files = False
        total_size = 0
        location_path = Path(location)
        
        for line in result.stdout.split("\n"):
            if line.startswith("Files:"):
                in_files = True
                continue
            
            if in_files and line.strip():
                file_path = location_path / line.strip()
                try:
                    if file_path.exists():
                        total_size += file_path.stat().st_size
                except (OSError, PermissionError):
                    pass
        
        return total_size
    
    except Exception:
        return 0


def uninstall_package(package_name: str) -> tuple[bool, str]:
    """
    Uninstall a single package.
    
    Returns:
        Tuple of (success, error_message)
    """
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "uninstall", "-y", package_name],
            capture_output=True,
            text=True,
            timeout=60,
        )
        
        if result.returncode == 0:
            return True, ""
        else:
            return False, result.stderr.strip()
    
    except subprocess.TimeoutExpired:
        return False, "Uninstall timed out"
    except Exception as e:
        return False, str(e)


def prune_python(
    project_path: Path | None = None,
    dry_run: bool = True,
    force: bool = False,
) -> PruneResult:
    """
    Prune unused Python packages.
    
    Args:
        project_path: Path to the project. If None, uses current directory.
        dry_run: If True, only show what would be removed.
        force: If True, skip confirmation prompt.
    
    Returns:
        PruneResult with operation results.
    """
    result = PruneResult(dry_run=dry_run)
    
    # Safety check: must be in a virtual environment
    if not is_in_virtualenv():
        error("Not running in a virtual environment!")
        error("Refusing to remove packages from system Python.")
        error("Activate a virtual environment and try again.")
        result.errors.append("Not in virtual environment")
        return result
    
    # Scan for unused packages
    info("Scanning Python project for unused dependencies...")
    scan_result = scan_python_project(project_path)
    
    if not scan_result.unused_packages:
        success("No unused packages found. Your project is clean!")
        return result
    
    # Get sizes and prepare list
    packages_to_remove: list[tuple[str, int]] = []
    
    for pkg_name in scan_result.unused_packages:
        # Double-check protected packages
        if pkg_name.lower() in PYTHON_PROTECTED_PACKAGES:
            continue
        
        size = get_package_size(pkg_name)
        packages_to_remove.append((pkg_name, size))
    
    if not packages_to_remove:
        success("No removable packages found.")
        return result
    
    # Sort by size (largest first)
    packages_to_remove.sort(key=lambda x: x[1], reverse=True)
    
    # Display what would be removed
    total_size = sum(size for _, size in packages_to_remove)
    
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Packages to remove:\n")
    
    colors_enabled = is_tty()
    
    for pkg_name, size in packages_to_remove:
        size_str = format_size(size) if size > 0 else "unknown"
        if colors_enabled:
            print(f"  {Colors.YELLOW}•{Colors.RESET} {pkg_name} ({size_str})")
        else:
            print(f"  • {pkg_name} ({size_str})")
    
    print(f"\nTotal: {len(packages_to_remove)} packages, ~{format_size(total_size)}")
    
    if dry_run:
        print(f"\n{Colors.CYAN if colors_enabled else ''}Use --force to actually remove these packages.{Colors.RESET if colors_enabled else ''}")
        return result
    
    # Confirmation
    if not force:
        print()
        if not confirm_action("Are you sure you want to remove these packages?"):
            info("Aborted by user.")
            return result
    
    # Actually remove packages
    print()
    for pkg_name, size in packages_to_remove:
        info(f"Removing {pkg_name}...")
        ok, err = uninstall_package(pkg_name)
        
        if ok:
            result.packages_removed.append(pkg_name)
            result.bytes_freed += size
            success(f"Removed {pkg_name}")
        else:
            result.packages_failed.append((pkg_name, err))
            warn(f"Failed to remove {pkg_name}: {err}")
    
    # Summary
    print()
    if result.packages_removed:
        success(f"Removed {len(result.packages_removed)} packages, freed ~{format_size(result.bytes_freed)}")
    
    if result.packages_failed:
        warn(f"Failed to remove {len(result.packages_failed)} packages")
    
    return result


def get_prune_result_dict(result: PruneResult) -> dict:
    """Convert PruneResult to a JSON-serializable dictionary."""
    return {
        "dry_run": result.dry_run,
        "packages_removed": result.packages_removed,
        "packages_failed": [
            {"package": pkg, "error": err}
            for pkg, err in result.packages_failed
        ],
        "bytes_freed": result.bytes_freed,
        "errors": result.errors,
    }
