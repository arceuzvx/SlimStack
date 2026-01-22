"""Node.js package pruner with safety guards."""

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from slim.core.utils import (
    run_command,
    confirm_action,
    format_size,
    get_directory_size,
    error,
    warn,
    info,
    success,
    is_tty,
)
from slim.core.config import Colors
from slim.scanners.node_scanner import scan_node_project, NodeScanResult


@dataclass
class NodePruneResult:
    """Result of a Node.js prune operation."""
    packages_removed: list[str] = field(default_factory=list)
    packages_failed: list[tuple[str, str]] = field(default_factory=list)
    bytes_freed: int = 0
    dry_run: bool = True
    errors: list[str] = field(default_factory=list)


def uninstall_node_package(package_name: str, project_path: Path) -> tuple[bool, str]:
    """
    Uninstall a Node.js package using npm.
    
    Returns:
        Tuple of (success, error_message)
    """
    returncode, stdout, stderr = run_command(
        ["npm", "uninstall", package_name],
        cwd=project_path,
    )
    
    if returncode == 0:
        return True, ""
    else:
        return False, stderr.strip() if stderr else "Unknown error"


def check_npm_available() -> bool:
    """Check if npm is available in PATH."""
    returncode, _, _ = run_command(["npm", "--version"])
    return returncode == 0


def prune_node(
    project_path: Path | None = None,
    dry_run: bool = True,
    force: bool = False,
    include_dev: bool = False,
) -> NodePruneResult:
    """
    Prune unused Node.js packages.
    
    Args:
        project_path: Path to the project. If None, uses current directory.
        dry_run: If True, only show what would be removed.
        force: If True, skip confirmation prompt.
        include_dev: If True, also remove unused devDependencies.
    
    Returns:
        NodePruneResult with operation results.
    """
    result = NodePruneResult(dry_run=dry_run)
    
    if project_path is None:
        project_path = Path.cwd()
    
    # Check npm is available
    if not check_npm_available():
        error("npm is not available in PATH")
        result.errors.append("npm not found")
        return result
    
    # Check for package.json
    package_json = project_path / "package.json"
    if not package_json.exists():
        error(f"No package.json found in {project_path}")
        result.errors.append("No package.json")
        return result
    
    # Safety check: don't operate on global packages
    node_modules = project_path / "node_modules"
    if not node_modules.exists():
        info("No node_modules directory found. Nothing to prune.")
        return result
    
    # Scan for unused packages
    info("Scanning Node.js project for unused dependencies...")
    scan_result = scan_node_project(project_path)
    
    unused = scan_result.unused_packages
    if include_dev:
        unused = unused | scan_result.unused_dev_packages
    
    if not unused:
        success("No unused packages found. Your project is clean!")
        return result
    
    # Get sizes
    packages_to_remove: list[tuple[str, int]] = []
    
    for pkg_name in unused:
        size = scan_result.package_sizes.get(pkg_name, 0)
        packages_to_remove.append((pkg_name, size))
    
    # Sort by size (largest first)
    packages_to_remove.sort(key=lambda x: x[1], reverse=True)
    
    # Display what would be removed
    total_size = sum(size for _, size in packages_to_remove)
    
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Packages to remove:\n")
    
    colors_enabled = is_tty()
    
    for pkg_name, size in packages_to_remove:
        size_str = format_size(size) if size > 0 else "unknown"
        is_dev = pkg_name in scan_result.unused_dev_packages
        dev_marker = " (dev)" if is_dev else ""
        
        if colors_enabled:
            print(f"  {Colors.YELLOW}•{Colors.RESET} {pkg_name}{dev_marker} ({size_str})")
        else:
            print(f"  • {pkg_name}{dev_marker} ({size_str})")
    
    print(f"\nTotal: {len(packages_to_remove)} packages, ~{format_size(total_size)}")
    
    if dry_run:
        print(f"\n{Colors.CYAN if colors_enabled else ''}Use --force to actually remove these packages.{Colors.RESET if colors_enabled else ''}")
        return result
    
    # Confirmation
    if not force:
        print()
        warn("This will modify package.json and remove packages from node_modules.")
        if not confirm_action("Are you sure you want to remove these packages?"):
            info("Aborted by user.")
            return result
    
    # Actually remove packages
    print()
    for pkg_name, size in packages_to_remove:
        info(f"Removing {pkg_name}...")
        ok, err = uninstall_node_package(pkg_name, project_path)
        
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


def get_prune_result_dict(result: NodePruneResult) -> dict:
    """Convert NodePruneResult to a JSON-serializable dictionary."""
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
