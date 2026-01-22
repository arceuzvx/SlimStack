#!/usr/bin/env python3
"""
SlimStack CLI - Dependency hygiene and waste elimination.

Usage:
    slim help              Show help
    slim version           Show version
    
    slim py scan           Scan Python project dependencies
    slim py scan --json    Output as JSON
    slim py prune          Show unused packages (dry-run)
    slim py prune --force  Actually remove unused packages
    
    slim node scan         Scan Node.js project dependencies
    slim node scan --json  Output as JSON
    slim node prune        Show unused packages (dry-run)
    slim node prune --force Actually remove unused packages
    
    slim disk              Show disk usage by ecosystem
    slim disk --by project Show disk usage by project
    slim disk --top 10     Limit results
"""

import argparse
import sys
from pathlib import Path

from slim import __version__
from slim.core.config import Colors, VERSION
from slim.core.utils import (
    output_json,
    is_tty,
    error,
    info,
    format_size,
)


def cmd_version(args: argparse.Namespace) -> int:
    """Show version information."""
    print(f"SlimStack v{VERSION}")
    return 0


def cmd_help(args: argparse.Namespace) -> int:
    """Show help information."""
    print(__doc__)
    return 0


def cmd_py_scan(args: argparse.Namespace) -> int:
    """Scan Python project for dependencies."""
    from slim.scanners.python_scanner import scan_python_project, get_scan_result_dict
    from slim.visuals.tables import render_package_table, render_summary_box
    
    project_path = Path(args.path) if args.path else None
    result = scan_python_project(project_path)
    
    if args.json:
        output_json(get_scan_result_dict(result))
        return 0
    
    # Human-readable output
    colors_enabled = is_tty()
    
    print()
    if colors_enabled:
        print(f"{Colors.BOLD}SlimStack Python Dependency Scan{Colors.RESET}")
    else:
        print("SlimStack Python Dependency Scan")
    print("=" * 35)
    
    # Summary
    print(render_summary_box("Summary", [
        ("Project", str(result.project_path)),
        ("Virtual Env", "Yes" if result.in_virtualenv else "No"),
        ("Files Scanned", str(result.files_scanned)),
        ("Packages Installed", str(len(result.installed_packages))),
        ("Packages Used", str(len(result.used_packages))),
        ("Packages Unused", str(len(result.unused_packages))),
    ]))
    
    # Unused packages
    if result.unused_packages:
        print()
        if colors_enabled:
            print(f"{Colors.YELLOW}Unused Packages:{Colors.RESET}")
        else:
            print("Unused Packages:")
        
        for pkg in sorted(result.unused_packages):
            pkg_info = result.installed_packages.get(pkg)
            version = pkg_info.version if pkg_info else "?"
            print(f"  • {pkg} ({version})")
        
        print(f"\n→ Run 'slim py prune' to see removal options")
    else:
        print(f"\n{Colors.GREEN if colors_enabled else ''}✓ No unused packages found!{Colors.RESET if colors_enabled else ''}")
    
    # Unknown imports
    if result.unknown_imports:
        print()
        if colors_enabled:
            print(f"{Colors.DIM}Unknown imports (couldn't map to packages):{Colors.RESET}")
        else:
            print("Unknown imports (couldn't map to packages):")
        for imp in sorted(result.unknown_imports)[:10]:
            print(f"  ? {imp}")
        if len(result.unknown_imports) > 10:
            print(f"  ... and {len(result.unknown_imports) - 10} more")
    
    return 0


def cmd_py_prune(args: argparse.Namespace) -> int:
    """Prune unused Python packages."""
    from slim.pruners.python_pruner import prune_python, get_prune_result_dict
    
    project_path = Path(args.path) if args.path else None
    dry_run = not args.force
    
    result = prune_python(
        project_path=project_path,
        dry_run=dry_run,
        force=args.force,
    )
    
    if args.json:
        output_json(get_prune_result_dict(result))
    
    return 0 if not result.errors else 1


def cmd_node_scan(args: argparse.Namespace) -> int:
    """Scan Node.js project for dependencies."""
    from slim.scanners.node_scanner import scan_node_project, get_scan_result_dict
    from slim.visuals.tables import render_summary_box
    
    project_path = Path(args.path) if args.path else None
    result = scan_node_project(project_path)
    
    if args.json:
        output_json(get_scan_result_dict(result))
        return 0
    
    # Human-readable output
    colors_enabled = is_tty()
    
    print()
    if colors_enabled:
        print(f"{Colors.BOLD}SlimStack Node.js Dependency Scan{Colors.RESET}")
    else:
        print("SlimStack Node.js Dependency Scan")
    print("=" * 35)
    
    if not result.has_package_json:
        error("No package.json found in project.")
        return 1
    
    # Summary
    print(render_summary_box("Summary", [
        ("Project", str(result.project_path)),
        ("Files Scanned", str(result.files_scanned)),
        ("node_modules Size", format_size(result.node_modules_size)),
        ("Dependencies", str(len(result.dependencies))),
        ("Dev Dependencies", str(len(result.dev_dependencies))),
        ("Unused Deps", str(len(result.unused_packages))),
    ]))
    
    # Unused packages
    if result.unused_packages:
        print()
        if colors_enabled:
            print(f"{Colors.YELLOW}Unused Dependencies:{Colors.RESET}")
        else:
            print("Unused Dependencies:")
        
        for pkg in sorted(result.unused_packages):
            size = result.package_sizes.get(pkg, 0)
            size_str = format_size(size) if size > 0 else "?"
            print(f"  • {pkg} ({size_str})")
        
        print(f"\n→ Run 'slim node prune' to see removal options")
    else:
        print(f"\n{Colors.GREEN if colors_enabled else ''}✓ All dependencies are used!{Colors.RESET if colors_enabled else ''}")
    
    # Unused dev dependencies
    if result.unused_dev_packages:
        print()
        if colors_enabled:
            print(f"{Colors.DIM}Potentially unused devDependencies:{Colors.RESET}")
        else:
            print("Potentially unused devDependencies:")
        for pkg in sorted(result.unused_dev_packages)[:5]:
            print(f"  ? {pkg}")
        if len(result.unused_dev_packages) > 5:
            print(f"  ... and {len(result.unused_dev_packages) - 5} more")
        print("  (Note: devDeps may be used in config files or tests)")
    
    return 0


def cmd_node_prune(args: argparse.Namespace) -> int:
    """Prune unused Node.js packages."""
    from slim.pruners.node_pruner import prune_node, get_prune_result_dict
    
    project_path = Path(args.path) if args.path else None
    dry_run = not args.force
    
    result = prune_node(
        project_path=project_path,
        dry_run=dry_run,
        force=args.force,
        include_dev=args.include_dev,
    )
    
    if args.json:
        output_json(get_prune_result_dict(result))
    
    return 0 if not result.errors else 1


def cmd_disk(args: argparse.Namespace) -> int:
    """Show disk usage by ecosystem."""
    from slim.scanners.disk_scanner import scan_disk, get_scan_result_dict
    from slim.visuals.charts import render_disk_chart, render_project_chart
    from slim.visuals.tables import render_summary_box
    
    scan_path = Path(args.path) if args.path else None
    top_n = args.top if args.top else None
    
    info("Scanning disk usage (this may take a moment)...")
    result = scan_disk(scan_path, include_docker=True)
    
    if args.json:
        output_json(get_scan_result_dict(result, top_n))
        return 0
    
    # Human-readable output
    colors_enabled = is_tty()
    
    print()
    if colors_enabled:
        print(f"{Colors.BOLD}SlimStack Disk Usage Report{Colors.RESET}")
    else:
        print("SlimStack Disk Usage Report")
    print("=" * 30)
    
    if args.by_project:
        # Group by project
        if result.projects:
            projects = [
                (p.name, p.ecosystem, p.size_bytes)
                for p in result.projects
            ]
            if top_n:
                projects = projects[:top_n]
            
            print(render_project_chart(projects, title="Projects by Artifact Size"))
        else:
            print("  No projects found.")
    else:
        # Group by ecosystem
        print(render_disk_chart(
            python_size=result.python_usage.total_size,
            node_size=result.node_usage.total_size,
            docker_size=result.docker_usage.total_size,
        ))
        
        # Details for each ecosystem
        if result.python_usage.locations:
            print(f"\n{Colors.CYAN if colors_enabled else ''}Python virtual environments:{Colors.RESET if colors_enabled else ''}")
            locations = result.python_usage.locations[:top_n] if top_n else result.python_usage.locations
            for path, size in locations[:10]:
                print(f"  {format_size(size):>10}  {path}")
            if len(locations) > 10:
                print(f"  ... and {len(result.python_usage.locations) - 10} more")
        
        if result.node_usage.locations:
            print(f"\n{Colors.GREEN if colors_enabled else ''}Node.js node_modules:{Colors.RESET if colors_enabled else ''}")
            locations = result.node_usage.locations[:top_n] if top_n else result.node_usage.locations
            for path, size in locations[:10]:
                print(f"  {format_size(size):>10}  {path}")
            if len(locations) > 10:
                print(f"  ... and {len(result.node_usage.locations) - 10} more")
        
        if result.docker_usage.locations:
            print(f"\n{Colors.MAGENTA if colors_enabled else ''}Docker images:{Colors.RESET if colors_enabled else ''}")
            locations = result.docker_usage.locations[:top_n] if top_n else result.docker_usage.locations
            for name, size in locations[:10]:
                print(f"  {format_size(size):>10}  {name}")
            if len(locations) > 10:
                print(f"  ... and {len(result.docker_usage.locations) - 10} more")
    
    # Total
    total = (
        result.python_usage.total_size +
        result.node_usage.total_size +
        result.docker_usage.total_size
    )
    print(f"\n{'─' * 30}")
    print(f"Total: {format_size(total)}")
    
    return 0


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="slim",
        description="SlimStack - Dependency hygiene and waste elimination",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # version command
    version_parser = subparsers.add_parser("version", help="Show version")
    version_parser.set_defaults(func=cmd_version)
    
    # help command
    help_parser = subparsers.add_parser("help", help="Show help")
    help_parser.set_defaults(func=cmd_help)
    
    # py command (with subcommands)
    py_parser = subparsers.add_parser("py", help="Python commands")
    py_subparsers = py_parser.add_subparsers(dest="py_command", help="Python subcommands")
    
    # py scan
    py_scan_parser = py_subparsers.add_parser("scan", help="Scan Python dependencies")
    py_scan_parser.add_argument("--json", action="store_true", help="Output as JSON")
    py_scan_parser.add_argument("--path", "-p", help="Project path (default: current directory)")
    py_scan_parser.set_defaults(func=cmd_py_scan)
    
    # py prune
    py_prune_parser = py_subparsers.add_parser("prune", help="Remove unused Python packages")
    py_prune_parser.add_argument("--dry-run", action="store_true", help="Show what would be removed (default)")
    py_prune_parser.add_argument("--force", action="store_true", help="Actually remove packages")
    py_prune_parser.add_argument("--json", action="store_true", help="Output as JSON")
    py_prune_parser.add_argument("--path", "-p", help="Project path (default: current directory)")
    py_prune_parser.set_defaults(func=cmd_py_prune)
    
    # node command (with subcommands)
    node_parser = subparsers.add_parser("node", help="Node.js commands")
    node_subparsers = node_parser.add_subparsers(dest="node_command", help="Node.js subcommands")
    
    # node scan
    node_scan_parser = node_subparsers.add_parser("scan", help="Scan Node.js dependencies")
    node_scan_parser.add_argument("--json", action="store_true", help="Output as JSON")
    node_scan_parser.add_argument("--path", "-p", help="Project path (default: current directory)")
    node_scan_parser.set_defaults(func=cmd_node_scan)
    
    # node prune
    node_prune_parser = node_subparsers.add_parser("prune", help="Remove unused Node.js packages")
    node_prune_parser.add_argument("--dry-run", action="store_true", help="Show what would be removed (default)")
    node_prune_parser.add_argument("--force", action="store_true", help="Actually remove packages")
    node_prune_parser.add_argument("--include-dev", action="store_true", help="Also remove unused devDependencies")
    node_prune_parser.add_argument("--json", action="store_true", help="Output as JSON")
    node_prune_parser.add_argument("--path", "-p", help="Project path (default: current directory)")
    node_prune_parser.set_defaults(func=cmd_node_prune)
    
    # disk command
    disk_parser = subparsers.add_parser("disk", help="Disk usage analysis")
    disk_parser.add_argument("--by", dest="by_project", action="store_const", const=True, help="Group by project")
    disk_parser.add_argument("--top", type=int, help="Limit number of results")
    disk_parser.add_argument("--json", action="store_true", help="Output as JSON")
    disk_parser.add_argument("--path", "-p", help="Path to scan (default: current directory)")
    disk_parser.set_defaults(func=cmd_disk)
    
    return parser


def main() -> int:
    """Main entry point."""
    # Disable colors if not a TTY
    if not is_tty():
        Colors.disable()
    
    parser = create_parser()
    args = parser.parse_args()
    
    # Handle no command
    if args.command is None:
        parser.print_help()
        return 0
    
    # Handle subcommand requirements
    if args.command == "py" and getattr(args, "py_command", None) is None:
        print("Usage: slim py {scan|prune}")
        return 1
    
    if args.command == "node" and getattr(args, "node_command", None) is None:
        print("Usage: slim node {scan|prune}")
        return 1
    
    # Execute command
    if hasattr(args, "func"):
        try:
            return args.func(args)
        except KeyboardInterrupt:
            print("\nAborted.")
            return 130
        except Exception as e:
            error(f"Unexpected error: {e}")
            return 1
    
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
