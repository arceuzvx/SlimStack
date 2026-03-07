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
  - `slim man` - Display detailed manual
  - `slim scan -py` - Scan Python dependencies
  - `slim scan -node` - Scan Node.js dependencies  
  - `slim prune -py` - Remove unused Python packages
  - `slim prune -node` - Remove unused Node packages
  - `slim disk` - Disk usage analysis
  - `slim docker` - Dockerfile security and optimization analysis

- **Dockerfile Analysis** (NEW)
  - Security anti-pattern detection (secrets in ENV, running as root, etc.)
  - Hardened image recommendations (Chainguard, Alpine, distroless)
  - Multi-stage build detection
  - Best practice suggestions (HEALTHCHECK, COPY vs ADD, etc.)
  - Severity filtering and security-only mode
  - JSON output for CI/CD pipelines

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
  - Built-in manual (`slim man`)

## [0.2.0] - 2026-03-08

Major release with bug fixes, new features, performance improvements, and 205 unit tests.

### Fixed

- **Broken `slim docker` command** — `is_already_optimized` import was missing from `docker_images.py`
- **Hardened image detection** — `is_hardened_image()` never matched Chainguard/distroless registries due to prefix comparison bug

### Added

- **Configuration file support** (`.slimrc.toml`)
  - Exclude packages, set default flags, per-ecosystem settings
  - Walks up directory tree, falls back to home directory
  - `[python]`, `[node]`, `[docker]`, `[defaults]` sections

- **CI integration**
  - `--fail-on-unused` flag returns exit code 1 when unused packages found
  - Configurable via `.slimrc.toml`: `fail_on_unused = true`
  - GitHub Actions workflow template (`.github/workflows/slimstack.yml`)
  - Pre-commit hooks (`.pre-commit-hooks.yaml`)

- **Cache cleanup command** (`slim clean`)
  - Scans for `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `.next`, `node_modules/.cache`
  - Dry-run by default, `--force` to delete, `-i` for interactive selection
  - `--include-builds` for dist/build/out directories

- **Declared dependency parsing**
  - `requirements.txt` parsing with version spec support
  - `pyproject.toml` parsing (PEP 621 + Poetry format)
  - Warns about "declared but not installed" packages
  - Shows "installed but not declared" in verbose mode

- **Transitive dependency analysis**
  - Builds reverse dependency graph via `importlib.metadata`
  - Classifies packages as directly-used, transitive-only, or truly unused

- **CLI enhancements**
  - `--verbose` / `--quiet` global flags
  - `--exclude PKG ...` for scan and prune commands
  - Animated progress spinner for long operations
  - `.dockerignore`-aware COPY . . warning (downgraded to info when present)

- **Test suite** — 205 unit tests across 8 test files
  - Tests for utils, docker_images, python_scanner, node_scanner, docker_scanner, config_loader, deps_parser, cache_scanner

### Changed

- **Python scanning uses `importlib.metadata`** instead of `pip freeze` subprocess — instant, no 30s timeout
- **Import-to-package mappings** expanded from 15 to 55+ entries (ML, web, database, crypto, DevOps, utilities)
- **Node.js scanner** uses `bisect`-based line offset index — O(log n) lookups instead of O(n×m)
- `IMPORT_TO_PACKAGE` moved from function-local to module-level constant
- Added `pytest` to optional dev dependencies in `pyproject.toml`

## [Unreleased]

### Planned

- Monorepo support (pnpm-workspace, lerna)
- Interactive prune mode with arrow-key selection
- Yarn/pnpm package manager support


[0.1.0]: https://github.com/arceuzvx/SlimStack/releases/tag/v0.1.0
[0.2.0]: https://github.com/arceuzvx/SlimStack/releases/tag/v0.2.0
[Unreleased]: https://github.com/arceuzvx/SlimStack/compare/v0.2.0...HEAD
