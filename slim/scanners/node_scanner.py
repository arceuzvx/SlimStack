"""Node.js dependency scanner using regex-based import detection."""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

from slim.core.config import (
    NODE_EXTENSIONS,
    NODE_BUILTIN_MODULES,
    SKIP_DIRECTORIES,
)
from slim.core.utils import (
    get_directory_size,
    find_project_root,
)


@dataclass
class NodePackageInfo:
    """Information about a Node.js package."""
    name: str
    version: str
    is_dev: bool = False
    size_bytes: int = 0


@dataclass
class NodeImportInfo:
    """Information about an import found in JS/TS source."""
    module_name: str
    file_path: Path
    line_number: int
    import_type: str = "unknown"  # "require", "import", "dynamic"


@dataclass
class NodeScanResult:
    """Result of scanning a Node.js project."""
    project_path: Path
    has_package_json: bool = False
    
    # Dependencies from package.json
    dependencies: dict[str, NodePackageInfo] = field(default_factory=dict)
    dev_dependencies: dict[str, NodePackageInfo] = field(default_factory=dict)
    
    # Imports found in source
    used_imports: set[str] = field(default_factory=set)
    import_details: list[NodeImportInfo] = field(default_factory=list)
    
    # Classification
    used_packages: set[str] = field(default_factory=set)
    unused_packages: set[str] = field(default_factory=set)
    unused_dev_packages: set[str] = field(default_factory=set)
    
    # Size info
    node_modules_size: int = 0
    package_sizes: dict[str, int] = field(default_factory=dict)
    
    # Metadata
    files_scanned: int = 0
    errors: list[str] = field(default_factory=list)


# Regex patterns for import detection
REQUIRE_PATTERN = re.compile(
    r"""require\s*\(\s*['"]([^'"]+)['"]\s*\)""",
    re.MULTILINE
)

IMPORT_FROM_PATTERN = re.compile(
    r"""import\s+(?:(?:\{[^}]*\}|\*\s+as\s+\w+|\w+)\s*,?\s*)*\s*from\s*['"]([^'"]+)['"]""",
    re.MULTILINE
)

IMPORT_SIDE_EFFECT_PATTERN = re.compile(
    r"""import\s*['"]([^'"]+)['"]""",
    re.MULTILINE
)

DYNAMIC_IMPORT_PATTERN = re.compile(
    r"""import\s*\(\s*['"]([^'"]+)['"]\s*\)""",
    re.MULTILINE
)


def get_package_name(import_path: str) -> str | None:
    """
    Extract the package name from an import path.
    
    Examples:
        "lodash" -> "lodash"
        "lodash/get" -> "lodash"
        "@types/node" -> "@types/node"
        "@angular/core/testing" -> "@angular/core"
        "./local" -> None (local import)
        "../utils" -> None (relative import)
    """
    # Skip relative imports
    if import_path.startswith(".") or import_path.startswith("/"):
        return None
    
    # Skip Node.js builtins
    if import_path in NODE_BUILTIN_MODULES:
        return None
    
    # Handle scoped packages (@org/package)
    if import_path.startswith("@"):
        parts = import_path.split("/")
        if len(parts) >= 2:
            return f"{parts[0]}/{parts[1]}"
        return import_path
    
    # Regular package - just the first segment
    return import_path.split("/")[0]


def parse_package_json(package_json_path: Path) -> tuple[dict[str, NodePackageInfo], dict[str, NodePackageInfo]]:
    """Parse package.json and return dependencies and devDependencies."""
    dependencies: dict[str, NodePackageInfo] = {}
    dev_dependencies: dict[str, NodePackageInfo] = {}
    
    try:
        content = json.loads(package_json_path.read_text(encoding="utf-8"))
        
        # Parse regular dependencies
        for name, version in content.get("dependencies", {}).items():
            dependencies[name] = NodePackageInfo(
                name=name,
                version=version,
                is_dev=False,
            )
        
        # Parse dev dependencies
        for name, version in content.get("devDependencies", {}).items():
            dev_dependencies[name] = NodePackageInfo(
                name=name,
                version=version,
                is_dev=True,
            )
    
    except (json.JSONDecodeError, FileNotFoundError, PermissionError) as e:
        pass
    
    return dependencies, dev_dependencies


def extract_imports_from_file(file_path: Path) -> Iterator[NodeImportInfo]:
    """Extract all imports from a JS/TS file."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return
    
    # Pre-build line offset index for O(log n) lookups
    import bisect
    line_offsets: list[int] = []
    offset = 0
    for line in content.split("\n"):
        line_offsets.append(offset)
        offset += len(line) + 1  # +1 for newline
    
    def find_line_number(match_start: int) -> int:
        return bisect.bisect_right(line_offsets, match_start)
    
    # Find require() calls
    for match in REQUIRE_PATTERN.finditer(content):
        yield NodeImportInfo(
            module_name=match.group(1),
            file_path=file_path,
            line_number=find_line_number(match.start()),
            import_type="require",
        )
    
    # Find import ... from '...'
    for match in IMPORT_FROM_PATTERN.finditer(content):
        yield NodeImportInfo(
            module_name=match.group(1),
            file_path=file_path,
            line_number=find_line_number(match.start()),
            import_type="import",
        )
    
    # Find side-effect imports: import 'module'
    for match in IMPORT_SIDE_EFFECT_PATTERN.finditer(content):
        # Avoid duplicates with IMPORT_FROM_PATTERN
        module = match.group(1)
        if not any(m.module_name == module for m in IMPORT_FROM_PATTERN.finditer(content[:match.end()])):
            yield NodeImportInfo(
                module_name=module,
                file_path=file_path,
                line_number=find_line_number(match.start()),
                import_type="import",
            )
    
    # Find dynamic imports: import('module')
    for match in DYNAMIC_IMPORT_PATTERN.finditer(content):
        yield NodeImportInfo(
            module_name=match.group(1),
            file_path=file_path,
            line_number=find_line_number(match.start()),
            import_type="dynamic",
        )


def find_js_files(root: Path) -> Iterator[Path]:
    """Find all JS/TS files in a directory, respecting skip rules."""
    try:
        for entry in root.iterdir():
            if entry.is_dir():
                if entry.name in SKIP_DIRECTORIES:
                    continue
                if entry.name.startswith("."):
                    continue
                yield from find_js_files(entry)
            elif entry.is_file() and entry.suffix in NODE_EXTENSIONS:
                yield entry
    except PermissionError:
        pass


def calculate_package_sizes(project_path: Path, packages: list[str]) -> dict[str, int]:
    """Calculate the size of each installed package in node_modules."""
    sizes: dict[str, int] = {}
    node_modules = project_path / "node_modules"
    
    if not node_modules.exists():
        return sizes
    
    for pkg in packages:
        if pkg.startswith("@"):
            # Scoped package: @org/package
            pkg_path = node_modules / pkg
        else:
            pkg_path = node_modules / pkg
        
        if pkg_path.exists():
            sizes[pkg] = get_directory_size(pkg_path)
    
    return sizes


def scan_node_project(project_path: Path | None = None) -> NodeScanResult:
    """
    Scan a Node.js project for dependencies.
    
    Args:
        project_path: Path to the project root. If None, uses current directory.
    
    Returns:
        NodeScanResult with all dependency information.
    """
    if project_path is None:
        project_path = find_project_root()
    
    result = NodeScanResult(project_path=project_path)
    
    # Check for package.json
    package_json_path = project_path / "package.json"
    if not package_json_path.exists():
        result.errors.append("No package.json found in project root")
        return result
    
    result.has_package_json = True
    
    # Parse package.json
    result.dependencies, result.dev_dependencies = parse_package_json(package_json_path)
    
    # Calculate node_modules size
    node_modules = project_path / "node_modules"
    if node_modules.exists():
        result.node_modules_size = get_directory_size(node_modules)
    
    # Scan all JS/TS files
    for js_file in find_js_files(project_path):
        result.files_scanned += 1
        
        for import_info in extract_imports_from_file(js_file):
            result.import_details.append(import_info)
            
            # Extract package name
            pkg_name = get_package_name(import_info.module_name)
            if pkg_name:
                result.used_imports.add(pkg_name)
    
    # Classify dependencies
    all_deps = set(result.dependencies.keys())
    all_dev_deps = set(result.dev_dependencies.keys())
    
    for pkg in all_deps:
        if pkg in result.used_imports:
            result.used_packages.add(pkg)
        else:
            result.unused_packages.add(pkg)
    
    for pkg in all_dev_deps:
        # Dev dependencies are trickier - they might be used in config files, tests, etc.
        # We still report them but mark as dev
        if pkg not in result.used_imports:
            result.unused_dev_packages.add(pkg)
    
    # Calculate package sizes
    all_packages = list(all_deps | all_dev_deps)
    result.package_sizes = calculate_package_sizes(project_path, all_packages)
    
    return result


def get_scan_result_dict(result: NodeScanResult) -> dict:
    """Convert NodeScanResult to a JSON-serializable dictionary."""
    return {
        "project_path": str(result.project_path),
        "has_package_json": result.has_package_json,
        "files_scanned": result.files_scanned,
        "node_modules_size_bytes": result.node_modules_size,
        "dependencies": {
            "total": len(result.dependencies),
            "used": sorted(result.used_packages),
            "unused": sorted(result.unused_packages),
        },
        "dev_dependencies": {
            "total": len(result.dev_dependencies),
            "unused": sorted(result.unused_dev_packages),
        },
        "package_sizes": {
            pkg: size for pkg, size in sorted(
                result.package_sizes.items(), 
                key=lambda x: x[1], 
                reverse=True
            )
        },
        "errors": result.errors,
    }
