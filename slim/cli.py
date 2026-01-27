#!/usr/bin/env python3
"""
SlimStack CLI - Dependency hygiene and waste elimination.

Usage:
    slim help              Show help
    slim man               Show detailed manual
    slim version           Show version
    
    slim scan -py          Scan Python project dependencies
    slim scan -py --json   Output as JSON
    slim scan -node        Scan Node.js project dependencies
    slim scan -node --json Output as JSON
    
    slim prune -py         Show unused Python packages (dry-run)
    slim prune -py --force Actually remove unused packages
    slim prune -node       Show unused Node.js packages (dry-run)
    slim prune -node --force Actually remove unused packages
    
    slim disk              Show disk usage by ecosystem
    slim disk --by project Show disk usage by project
    slim disk --top 10     Limit results
    
    slim docker            Analyze Dockerfile for issues
    slim docker --json     Output as JSON
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


def cmd_man(args: argparse.Namespace) -> int:
    """Show detailed manual."""
    colors_enabled = is_tty()
    
    # Color helpers
    def bold(text: str) -> str:
        return f"{Colors.BOLD}{text}{Colors.RESET}" if colors_enabled else text
    
    def cyan(text: str) -> str:
        return f"{Colors.CYAN}{text}{Colors.RESET}" if colors_enabled else text
    
    def yellow(text: str) -> str:
        return f"{Colors.YELLOW}{text}{Colors.RESET}" if colors_enabled else text
    
    def green(text: str) -> str:
        return f"{Colors.GREEN}{text}{Colors.RESET}" if colors_enabled else text
    
    def dim(text: str) -> str:
        return f"{Colors.DIM}{text}{Colors.RESET}" if colors_enabled else text
    
    def magenta(text: str) -> str:
        return f"{Colors.MAGENTA}{text}{Colors.RESET}" if colors_enabled else text
    
    manual = f"""
{bold("━" * 70)}
{bold("                         SLIMSTACK MANUAL")}
{bold("━" * 70)}

{bold("NAME")}
    {cyan("slim")} - dependency hygiene and waste elimination CLI tool

{bold("VERSION")}
    SlimStack v{VERSION}

{bold("SYNOPSIS")}
    {cyan("slim")} <command> [options]
    {cyan("slim")} <command> {yellow("-py")} | {yellow("-node")} [options]

{bold("━" * 70)}
{bold("                              DESCRIPTION")}
{bold("━" * 70)}

SlimStack is a CLI tool that helps developers identify, visualize, and 
safely remove unused dependencies and dependency bloat across Python 
and Node.js projects.

It uses {green("static analysis")} to determine which installed packages are 
actually being used:
  • {cyan("Python")}:  AST-based import detection (accurate, handles all syntax)
  • {cyan("Node.js")}: Regex-based require/import detection (fast, comprehensive)

{bold("KEY BENEFITS")}
  ✓ Reduce project size and attack surface
  ✓ Speed up CI/CD pipelines and Docker builds
  ✓ Keep dependencies clean and maintainable
  ✓ Visualize disk usage across projects

{bold("━" * 70)}
{bold("                               COMMANDS")}
{bold("━" * 70)}

{bold("GENERAL COMMANDS")}

  {cyan("slim version")}
      Display the current version of SlimStack.

  {cyan("slim help")}
      Display quick usage help and examples.

  {cyan("slim man")}
      Display this detailed manual.

{bold("SCAN COMMANDS")} {dim("(read-only, never modifies anything)")}

  {cyan("slim scan -py")} [options]
      Scan the current Python project for dependencies.
      Detects which installed packages are used, unused, or transitive-only.

      {yellow("Options:")}
        {green("--json")}        Output results as JSON for CI/CD pipelines
        {green("--path, -p")}    Specify project path (default: current directory)

      {yellow("What it analyzes:")}
        • All .py files in the project (excluding venv, __pycache__)
        • Installed packages via pip freeze
        • Import statements using Python's AST module

  {cyan("slim scan -node")} [options]
      Scan the current Node.js project for dependencies.
      Reads package.json and compares against actual imports in source files.

      {yellow("Options:")}
        {green("--json")}        Output results as JSON
        {green("--path, -p")}    Specify project path (default: current directory)

      {yellow("What it analyzes:")}
        • All .js, .jsx, .ts, .tsx, .mjs, .cjs files
        • package.json dependencies and devDependencies
        • require() calls and ESM import statements

{bold("PRUNE COMMANDS")} {dim("(dry-run by default, safe)")}

  {cyan("slim prune -py")} [options]
      Show unused Python packages that can be removed.
      {yellow("Default is dry-run mode")} - no changes are made.

      {yellow("Options:")}
        {green("--force")}       Actually remove packages (with confirmation)
        {green("--dry-run")}     Show what would be removed (default)
        {green("--json")}        Output results as JSON
        {green("--path, -p")}    Specify project path

      {yellow("Requirements:")}
        • Must be running inside a virtual environment
        • Protected packages (pip, setuptools, wheel) are never removed

  {cyan("slim prune -node")} [options]
      Show unused Node.js packages that can be removed.

      {yellow("Options:")}
        {green("--force")}       Actually remove packages via npm uninstall
        {green("--include-dev")} Include unused devDependencies in removal
        {green("--dry-run")}     Show what would be removed (default)
        {green("--json")}        Output results as JSON
        {green("--path, -p")}    Specify project path

{bold("DISK USAGE COMMANDS")} {dim("(read-only)")}

  {cyan("slim disk")} [options]
      Show disk usage by ecosystem with ASCII bar charts.
      Scans for Python venvs, node_modules, and Docker images.

      {yellow("Options:")}
        {green("--by project")}  Group by project instead of ecosystem
        {green("--top N")}       Limit results to top N items by size
        {green("--path, -p")}    Scan a specific directory
        {green("--json")}        Output as JSON

{bold("━" * 70)}
{bold("                           SAFETY FEATURES")}
{bold("━" * 70)}

SlimStack is designed with {green("safety as the #1 priority")}:

  {green("✓ Read-only by default")}
    All scan commands never modify anything on disk.

  {green("✓ Dry-run for prune")}
    Prune commands only show what would be removed unless --force is used.

  {green("✓ Confirmation prompts")}
    The --force flag requires explicit "y" confirmation before any deletion.

  {green("✓ Virtual environment protection")}
    Python pruning REQUIRES running inside a virtual environment.
    This prevents accidental damage to your system Python installation.

  {green("✓ Protected packages")}
    Critical packages are NEVER removed:
      • pip, setuptools, wheel (Python)
      • npm itself is never touched (Node.js)

  {green("✓ Project-local only")}
    Only operates on project-local dependencies, never global packages.

{bold("━" * 70)}
{bold("                         DETECTION METHODS")}
{bold("━" * 70)}

{bold("PYTHON IMPORT DETECTION")}

  SlimStack uses Python's {cyan("ast")} module for accurate static analysis:

    {green("✓ Detected:")}
      import requests
      from flask import Flask
      from PIL import Image
      import numpy as np

    {yellow("⚠ Skipped (stdlib):")}
      import os
      import sys
      from pathlib import Path

    {yellow("⚠ Not detected (dynamic):")}
      module = __import__(name)
      importlib.import_module(name)

  {dim("Note: Dynamic imports are logged as 'unknown' for manual review.")}

{bold("PACKAGE NAME MAPPING")}

  SlimStack handles packages where import name differs from package name:

    {dim("Package Name")}     →  {dim("Import Name")}
    ─────────────────────────────────
    Pillow            →  PIL
    opencv-python     →  cv2
    scikit-learn      →  sklearn
    beautifulsoup4    →  bs4
    python-dateutil   →  dateutil
    PyYAML            →  yaml
    python-dotenv     →  dotenv

{bold("NODE.JS IMPORT DETECTION")}

  SlimStack uses regex patterns to detect JavaScript imports:

    {green("✓ Detected:")}
      const express = require('express');
      import React from 'react';
      import {{ useState }} from 'react';
      import('./dynamic-module');
      require.resolve('package');

    {yellow("⚠ Not detected (relative paths):")}
      import utils from './utils';
      require('../lib/helper');

    {yellow("⚠ Not detected (variable):")}
      require(packageName);

{bold("━" * 70)}
{bold("                              EXAMPLES")}
{bold("━" * 70)}

{bold("Basic Python Workflow")}

  {dim("# 1. Scan to see what's unused")}
  $ {cyan("slim scan -py")}

  {dim("# 2. Preview what would be removed")}
  $ {cyan("slim prune -py")}

  {dim("# 3. Actually remove unused packages")}
  $ {cyan("slim prune -py --force")}

{bold("Basic Node.js Workflow")}

  {dim("# 1. Scan the project")}
  $ {cyan("slim scan -node")}

  {dim("# 2. Preview removal (including devDeps)")}
  $ {cyan("slim prune -node --include-dev")}

  {dim("# 3. Remove unused packages")}
  $ {cyan("slim prune -node --force")}

{bold("CI/CD Integration")}

  {dim("# Get JSON output for automated processing")}
  $ {cyan("slim scan -py --json")} > deps.json

  {dim("# Check for unused deps in CI pipeline")}
  $ {cyan("slim scan -node --json")} | jq '.unused_packages | length'

{bold("Disk Usage Analysis")}

  {dim("# See overall ecosystem usage")}
  $ {cyan("slim disk")}

  {dim("# Find heaviest projects")}
  $ {cyan("slim disk --by project --top 10")}

  {dim("# Scan a specific directory")}
  $ {cyan("slim disk --path ~/projects --top 5")}

{bold("━" * 70)}
{bold("                           JSON OUTPUT")}
{bold("━" * 70)}

All commands support {green("--json")} for machine-readable output:

{bold("Python Scan JSON Structure")}
  {{
    "project_path": "/path/to/project",
    "in_virtualenv": true,
    "files_scanned": 42,
    "packages": {{
      "total": 28,
      "used": ["flask", "requests"],
      "unused": ["black", "isort"],
      "transitive_only": []
    }},
    "unknown_imports": ["mymodule"]
  }}

{bold("Node.js Scan JSON Structure")}
  {{
    "project_path": "/path/to/project",
    "has_package_json": true,
    "files_scanned": 156,
    "node_modules_size_bytes": 257294336,
    "dependencies": {{"express": "4.18.0"}},
    "dev_dependencies": {{"jest": "29.0.0"}},
    "unused_packages": ["lodash", "moment"],
    "unused_dev_packages": ["@types/unused"]
  }}

{bold("━" * 70)}
{bold("                          TROUBLESHOOTING")}
{bold("━" * 70)}

{yellow("Q: Why are some packages marked as unused when I use them?")}
  A: SlimStack uses static analysis. It cannot detect:
     • Dynamic imports: __import__(name), importlib.import_module()
     • String-based requires: require(variable)
     • Packages used only in config files (webpack, babel, etc.)
     • Pytest plugins, Django apps loaded via settings

{yellow("Q: Why does Python prune require a virtual environment?")}
  A: This is a safety feature to prevent accidentally removing system
     packages. Always work in a virtual environment for Python development.

{yellow("Q: Why are devDependencies shown as unused?")}
  A: devDependencies are often used by tooling (webpack, jest, eslint)
     rather than imported directly. Use --include-dev cautiously.

{yellow("Q: How do I exclude certain packages from pruning?")}
  A: Currently, manually review the dry-run output before using --force.
     Configuration file support is planned for a future release.

{bold("━" * 70)}
{bold("                            EXIT CODES")}
{bold("━" * 70)}

  {green("0")}   - Success
  {yellow("1")}   - Error (missing package.json, not in virtualenv, etc.)
  {yellow("130")} - Interrupted by user (Ctrl+C)

{bold("━" * 70)}
{bold("                           MORE INFO")}
{bold("━" * 70)}

  {cyan("Repository")}:   https://github.com/arceuzvx/SlimStack
  {cyan("Issues")}:       https://github.com/arceuzvx/SlimStack/issues
  {cyan("License")}:      MIT License
  {cyan("Author")}:       arceuzvx

{bold("━" * 70)}
"""
    
    print(manual)
    return 0


def _scan_python(args: argparse.Namespace) -> int:
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
        
        print(f"\n→ Run 'slim prune -py' to see removal options")
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


def _prune_python(args: argparse.Namespace) -> int:
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


def _scan_node(args: argparse.Namespace) -> int:
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
        
        print(f"\n→ Run 'slim prune -node' to see removal options")
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


def _prune_node(args: argparse.Namespace) -> int:
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


def cmd_scan(args: argparse.Namespace) -> int:
    """Dispatch scan command to appropriate language scanner."""
    if args.lang_py:
        return _scan_python(args)
    elif args.lang_node:
        return _scan_node(args)
    else:
        error("Please specify a language: -py or -node")
        return 1


def cmd_prune(args: argparse.Namespace) -> int:
    """Dispatch prune command to appropriate language pruner."""
    if args.lang_py:
        return _prune_python(args)
    elif args.lang_node:
        return _prune_node(args)
    else:
        error("Please specify a language: -py or -node")
        return 1


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


def cmd_docker_scan(args: argparse.Namespace) -> int:
    """Scan Dockerfile for security issues and optimization opportunities."""
    from slim.scanners.docker_scanner import scan_dockerfile, get_scan_result_dict
    
    project_path = Path(args.path) if args.path else None
    result = scan_dockerfile(project_path=project_path)
    
    if args.json:
        output_json(get_scan_result_dict(result))
        return 0
    
    # Human-readable output
    colors_enabled = is_tty()
    
    print()
    if colors_enabled:
        print(f"{Colors.BOLD}SlimStack Dockerfile Analysis{Colors.RESET}")
    else:
        print("SlimStack Dockerfile Analysis")
    print("=" * 32)
    
    # Check if Dockerfile was found
    if not result.base_images:
        if result.issues and result.issues[0].message == "No Dockerfile found":
            error("No Dockerfile found in project.")
            return 1
    
    # Show basic info
    print(f"\nDockerfile: {result.dockerfile_path}")
    print(f"Base images: {len(result.base_images)}")
    print(f"Multi-stage: {'Yes' if result.multi_stage else 'No'}")
    print(f"Runs as non-root: {'Yes' if result.has_user_instruction else 'No'}")
    print(f"Has HEALTHCHECK: {'Yes' if result.has_healthcheck else 'No'}")
    
    # Filter issues by severity if specified
    issues = result.issues
    min_severity = getattr(args, 'severity', None)
    if min_severity:
        severity_order = {"critical": 0, "warning": 1, "info": 2}
        min_level = severity_order.get(min_severity.lower(), 2)
        issues = [i for i in issues if severity_order.get(i.severity, 2) <= min_level]
    
    # Filter by security only if specified
    if getattr(args, 'security_only', False):
        issues = [i for i in issues if i.category == "security"]
    
    # Show issues
    if issues:
        print()
        if colors_enabled:
            print(f"{Colors.YELLOW}Issues Found ({len(issues)}):{Colors.RESET}")
        else:
            print(f"Issues Found ({len(issues)}):")
        
        for issue in issues:
            # Severity icon and color
            if issue.severity == "critical":
                icon = "🔴" if colors_enabled else "[CRITICAL]"
                color = Colors.RED if colors_enabled else ""
            elif issue.severity == "warning":
                icon = "🟡" if colors_enabled else "[WARNING]"
                color = Colors.YELLOW if colors_enabled else ""
            else:
                icon = "🔵" if colors_enabled else "[INFO]"
                color = Colors.CYAN if colors_enabled else ""
            
            reset = Colors.RESET if colors_enabled else ""
            
            print(f"\n  {icon} {color}Line {issue.line_number}: {issue.message}{reset}")
            print(f"     Category: {issue.category}")
            if colors_enabled:
                print(f"     {Colors.DIM}→ {issue.suggestion}{Colors.RESET}")
            else:
                print(f"     → {issue.suggestion}")
    else:
        print(f"\n{Colors.GREEN if colors_enabled else ''}✓ No issues found!{Colors.RESET if colors_enabled else ''}")
    
    # Show recommendations
    if result.recommendations:
        print()
        if colors_enabled:
            print(f"{Colors.CYAN}Image Recommendations:{Colors.RESET}")
        else:
            print("Image Recommendations:")
        
        shown = set()
        for rec in result.recommendations:
            if rec.recommended_image in shown:
                continue
            shown.add(rec.recommended_image)
            
            print(f"\n  Current:     {rec.current_image}")
            if colors_enabled:
                print(f"  {Colors.GREEN}Recommended: {rec.recommended_image}{Colors.RESET}")
            else:
                print(f"  Recommended: {rec.recommended_image}")
            print(f"  Reason:      {rec.reason} - {rec.description}")
            if rec.size_estimate:
                print(f"  Size:        {rec.size_estimate}")
    
    # Summary
    critical = sum(1 for i in result.issues if i.severity == "critical")
    warning = sum(1 for i in result.issues if i.severity == "warning")
    info_count = sum(1 for i in result.issues if i.severity == "info")
    
    print(f"\n{'─' * 32}")
    print(f"Summary: {critical} critical, {warning} warnings, {info_count} info")
    
    if result.recommendations:
        print(f"         {len(result.recommendations)} image recommendations")
    
    # Return non-zero if critical issues found
    return 1 if critical > 0 else 0


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
    
    # man command (detailed manual)
    man_parser = subparsers.add_parser("man", help="Show detailed manual")
    man_parser.set_defaults(func=cmd_man)
    
    # scan command with language flags
    scan_parser = subparsers.add_parser("scan", help="Scan project dependencies")
    scan_lang_group = scan_parser.add_mutually_exclusive_group(required=True)
    scan_lang_group.add_argument("-py", "--py", action="store_true", dest="lang_py", help="Scan Python project")
    scan_lang_group.add_argument("-node", "--node", action="store_true", dest="lang_node", help="Scan Node.js project")
    scan_parser.add_argument("--json", action="store_true", help="Output as JSON")
    scan_parser.add_argument("--path", "-p", help="Project path (default: current directory)")
    scan_parser.set_defaults(func=cmd_scan)
    
    # prune command with language flags
    prune_parser = subparsers.add_parser("prune", help="Remove unused packages")
    prune_lang_group = prune_parser.add_mutually_exclusive_group(required=True)
    prune_lang_group.add_argument("-py", "--py", action="store_true", dest="lang_py", help="Prune Python packages")
    prune_lang_group.add_argument("-node", "--node", action="store_true", dest="lang_node", help="Prune Node.js packages")
    prune_parser.add_argument("--dry-run", action="store_true", help="Show what would be removed (default)")
    prune_parser.add_argument("--force", action="store_true", help="Actually remove packages")
    prune_parser.add_argument("--include-dev", action="store_true", help="Also remove unused devDependencies (Node.js only)")
    prune_parser.add_argument("--json", action="store_true", help="Output as JSON")
    prune_parser.add_argument("--path", "-p", help="Project path (default: current directory)")
    prune_parser.set_defaults(func=cmd_prune)
    
    # disk command
    disk_parser = subparsers.add_parser("disk", help="Disk usage analysis")
    disk_parser.add_argument("--by", dest="by_project", action="store_const", const=True, help="Group by project")
    disk_parser.add_argument("--top", type=int, help="Limit number of results")
    disk_parser.add_argument("--json", action="store_true", help="Output as JSON")
    disk_parser.add_argument("--path", "-p", help="Path to scan (default: current directory)")
    disk_parser.set_defaults(func=cmd_disk)
    
    # docker scan command
    docker_parser = subparsers.add_parser("docker", help="Dockerfile analysis and optimization")
    docker_parser.add_argument("--json", action="store_true", help="Output as JSON")
    docker_parser.add_argument("--path", "-p", help="Project path (default: current directory)")
    docker_parser.add_argument("--severity", choices=["critical", "warning", "info"], 
                               help="Minimum severity to report")
    docker_parser.add_argument("--security-only", action="store_true", dest="security_only",
                               help="Only show security-related issues")
    docker_parser.set_defaults(func=cmd_docker_scan)
    
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
