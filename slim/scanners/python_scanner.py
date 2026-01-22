"""Python dependency scanner using AST-based import detection."""

import ast
import sys
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

from slim.core.config import (
    PYTHON_EXTENSIONS,
    PYTHON_PROTECTED_PACKAGES,
    PYTHON_STDLIB_PREFIXES,
    SKIP_DIRECTORIES,
)
from slim.core.utils import (
    is_in_virtualenv,
    get_virtualenv_path,
    find_project_root,
    warn,
)


@dataclass
class PackageInfo:
    """Information about an installed Python package."""
    name: str
    version: str
    location: str = ""
    size_bytes: int = 0


@dataclass 
class ImportInfo:
    """Information about an import found in source code."""
    module_name: str
    file_path: Path
    line_number: int
    is_from_import: bool = False


@dataclass
class ScanResult:
    """Result of scanning a Python project."""
    project_path: Path
    installed_packages: dict[str, PackageInfo] = field(default_factory=dict)
    used_imports: set[str] = field(default_factory=set)
    import_details: list[ImportInfo] = field(default_factory=list)
    
    # Classification results
    used_packages: set[str] = field(default_factory=set)
    unused_packages: set[str] = field(default_factory=set)
    transitive_only: set[str] = field(default_factory=set)
    unknown_imports: set[str] = field(default_factory=set)
    
    # Metadata
    files_scanned: int = 0
    errors: list[str] = field(default_factory=list)
    in_virtualenv: bool = False
    virtualenv_path: Path | None = None


def get_stdlib_modules() -> frozenset[str]:
    """Get the set of standard library module names."""
    # Python 3.10+ has sys.stdlib_module_names
    if hasattr(sys, 'stdlib_module_names'):
        return frozenset(sys.stdlib_module_names)
    # Fallback to our predefined list
    return PYTHON_STDLIB_PREFIXES


def normalize_package_name(name: str) -> str:
    """Normalize package name for comparison (PEP 503)."""
    return name.lower().replace("-", "_").replace(".", "_")


def get_top_level_module(import_name: str) -> str:
    """Extract the top-level module from an import path."""
    return import_name.split(".")[0]


def get_installed_packages() -> dict[str, PackageInfo]:
    """Get all installed packages using pip freeze."""
    packages: dict[str, PackageInfo] = {}
    
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "freeze"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        
        if result.returncode != 0:
            return packages
        
        for line in result.stdout.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            
            # Handle different formats: pkg==version, pkg @ path, etc.
            if "==" in line:
                name, version = line.split("==", 1)
            elif " @ " in line:
                name, version = line.split(" @ ", 1)
            elif ">=" in line:
                name, version = line.split(">=", 1)
            elif "<=" in line:
                name, version = line.split("<=", 1)
            else:
                name = line
                version = "unknown"
            
            name = name.strip()
            normalized = normalize_package_name(name)
            packages[normalized] = PackageInfo(
                name=name,
                version=version.strip(),
            )
    
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        pass
    
    return packages


def extract_imports_from_file(file_path: Path) -> Iterator[ImportInfo]:
    """Extract all imports from a Python file using AST."""
    try:
        source = file_path.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        # Log but don't fail on syntax errors
        return
    except Exception:
        return
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield ImportInfo(
                    module_name=alias.name,
                    file_path=file_path,
                    line_number=node.lineno,
                    is_from_import=False,
                )
        
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                yield ImportInfo(
                    module_name=node.module,
                    file_path=file_path,
                    line_number=node.lineno,
                    is_from_import=True,
                )
            # Handle relative imports (from . import x)
            elif node.level > 0:
                # Relative imports are internal, skip them
                pass


def find_python_files(root: Path) -> Iterator[Path]:
    """Find all Python files in a directory, respecting skip rules."""
    try:
        for entry in root.iterdir():
            if entry.is_dir():
                if entry.name in SKIP_DIRECTORIES:
                    continue
                if entry.name.startswith("."):
                    continue
                yield from find_python_files(entry)
            elif entry.is_file() and entry.suffix in PYTHON_EXTENSIONS:
                yield entry
    except PermissionError:
        pass


def map_import_to_package(import_name: str, packages: dict[str, PackageInfo]) -> str | None:
    """
    Try to map an import name to an installed package.
    
    This is tricky because package names don't always match import names.
    Common examples:
    - PIL -> Pillow
    - cv2 -> opencv-python
    - yaml -> PyYAML
    - sklearn -> scikit-learn
    """
    # Common import-to-package mappings
    IMPORT_TO_PACKAGE: dict[str, str] = {
        "pil": "pillow",
        "cv2": "opencv_python",
        "yaml": "pyyaml",
        "sklearn": "scikit_learn",
        "skimage": "scikit_image",
        "bs4": "beautifulsoup4",
        "dateutil": "python_dateutil",
        "dotenv": "python_dotenv",
        "jwt": "pyjwt",
        "serial": "pyserial",
        "usb": "pyusb",
        "magic": "python_magic",
        "gi": "pygobject",
        "wx": "wxpython",
    }
    
    normalized_import = normalize_package_name(import_name)
    
    # Direct match
    if normalized_import in packages:
        return normalized_import
    
    # Check known mappings
    if normalized_import in IMPORT_TO_PACKAGE:
        mapped = IMPORT_TO_PACKAGE[normalized_import]
        if mapped in packages:
            return mapped
    
    # Try variations
    variations = [
        f"python_{normalized_import}",
        f"py{normalized_import}",
        f"{normalized_import}_python",
    ]
    
    for var in variations:
        if var in packages:
            return var
    
    return None


def scan_python_project(project_path: Path | None = None) -> ScanResult:
    """
    Scan a Python project for dependencies.
    
    Args:
        project_path: Path to the project root. If None, uses current directory.
    
    Returns:
        ScanResult with all dependency information.
    """
    if project_path is None:
        project_path = find_project_root()
    
    result = ScanResult(
        project_path=project_path,
        in_virtualenv=is_in_virtualenv(),
        virtualenv_path=get_virtualenv_path(),
    )
    
    # Get installed packages
    result.installed_packages = get_installed_packages()
    
    # Get stdlib modules
    stdlib = get_stdlib_modules()
    
    # Scan all Python files
    for py_file in find_python_files(project_path):
        result.files_scanned += 1
        
        for import_info in extract_imports_from_file(py_file):
            result.import_details.append(import_info)
            
            top_level = get_top_level_module(import_info.module_name)
            normalized = normalize_package_name(top_level)
            
            # Skip stdlib
            if normalized in stdlib or top_level in stdlib:
                continue
            
            result.used_imports.add(normalized)
    
    # Classify packages
    for pkg_name in result.installed_packages:
        # Skip protected packages
        if pkg_name in PYTHON_PROTECTED_PACKAGES:
            continue
        
        # Check if directly used
        if pkg_name in result.used_imports:
            result.used_packages.add(pkg_name)
        else:
            # Check via mapping
            matched = False
            for imp in result.used_imports:
                mapped_pkg = map_import_to_package(imp, result.installed_packages)
                if mapped_pkg == pkg_name:
                    result.used_packages.add(pkg_name)
                    matched = True
                    break
            
            if not matched:
                result.unused_packages.add(pkg_name)
    
    # Find imports that couldn't be mapped to packages
    for imp in result.used_imports:
        if imp in stdlib:
            continue
        mapped = map_import_to_package(imp, result.installed_packages)
        if mapped is None and imp not in result.installed_packages:
            result.unknown_imports.add(imp)
    
    return result


def get_scan_result_dict(result: ScanResult) -> dict:
    """Convert ScanResult to a JSON-serializable dictionary."""
    return {
        "project_path": str(result.project_path),
        "in_virtualenv": result.in_virtualenv,
        "virtualenv_path": str(result.virtualenv_path) if result.virtualenv_path else None,
        "files_scanned": result.files_scanned,
        "packages": {
            "total": len(result.installed_packages),
            "used": sorted(result.used_packages),
            "unused": sorted(result.unused_packages),
            "transitive_only": sorted(result.transitive_only),
        },
        "unknown_imports": sorted(result.unknown_imports),
        "errors": result.errors,
    }
