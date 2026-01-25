# Changelog

All notable changes to SlimStack will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-01-23

Initial release of SlimStack - Dependency hygiene and waste elimination CLI tool.

### Added

- **Python Analysis**
  - AST-based import detection for Python source files
  - pip freeze parsing for installed package detection
  - Package classification (used, unused, transitive-only)
  - Import-to-package mapping for common packages (PIL, cv2, sklearn, etc.)
  - Virtual environment detection and protection

- **Node.js Analysis**
  - package.json parsing for declared dependencies
  - Regex-based require() and import detection
  - Support for ESM imports and dynamic imports
  - node_modules size estimation
  - devDependencies tracking

- **Disk Usage Analysis**
  - Ecosystem-based disk usage visualization
  - Project-based grouping option
  - Python virtual environment detection
  - Node.js node_modules detection
  - Docker image size reporting (read-only)
  - ASCII bar chart rendering

- **CLI Commands**
  - `slim version` - Display version
  - `slim help` - Show usage help
  - `slim scan -py` - Scan Python dependencies
  - `slim scan -node` - Scan Node.js dependencies  
  - `slim prune -py` - Remove unused Python packages
  - `slim prune -node` - Remove unused Node packages
  - `slim disk` - Disk usage analysis

- **Safety Features**
  - Read-only scan operations by default
  - Dry-run mode for prune commands (default)
  - Confirmation prompts for destructive actions
  - Virtual environment requirement for Python pruning
  - Protected packages (pip, setuptools, wheel)

- **Output Formats**
  - Human-readable ASCII tables and charts
  - JSON output (`--json` flag) for CI/CD integration
  - ANSI color support with automatic TTY detection

- **Documentation**
  - Comprehensive README with usage examples
  - Unix man page (`man slim`)

## [Unreleased]

### Planned

- Transitive dependency analysis
- Requirements.txt / pyproject.toml sync
- Monorepo support
- Cache cleanup (pytest, mypy, ruff)
- Interactive mode for package selection
- Configuration file support
- Pre-commit hook integration

[0.1.0]: https://github.com/arceuzvx/SlimStack/releases/tag/v0.1.0
[Unreleased]: https://github.com/arceuzvx/SlimStack/compare/v0.1.0...HEAD
