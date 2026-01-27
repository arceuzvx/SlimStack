# SlimStack

**Dependency hygiene and waste elimination for developers.**

SlimStack is a CLI tool that helps you identify, visualize, and safely remove unused dependencies and dependency bloat across Python and Node.js projects.

## Features

- **Python Analysis** - AST-based import detection, pip freeze parsing
- **Node.js Analysis** - package.json parsing, require/import detection
- **Disk Visualization** - ASCII charts for ecosystem usage
- **Safety First** - Read-only by default, confirmation prompts for deletions
- **JSON Output** - Machine-readable output for CI/CD integration

## Installation

```bash
# From source (development)
cd SlimStack
pip install -e .

# Verify installation
slim version
```

### Manual Page

View the full manual:
```bash
# On Linux/macOS (after install)
man slim

# Or view directly from source
man ./man/slim.1
```

## Usage

### Python Commands

```bash
# Scan current Python project
slim scan -py

# Scan with JSON output
slim scan -py --json

# Show unused packages (dry-run, safe)
slim prune -py

# Actually remove unused packages
slim prune -py --force
```

**Example output:**
```
SlimStack Python Dependency Scan
===================================
┌──────────────────────────────┐
│           Summary            │
├──────────────────────────────┤
│ Project          : myproject │
│ Virtual Env      :       Yes │
│ Files Scanned    :        42 │
│ Packages Installed :      28 │
│ Packages Used    :        15 │
│ Packages Unused  :        13 │
└──────────────────────────────┘

Unused Packages:
  - black (22.3.0)
  - isort (5.10.1)
  - pytest (7.1.2)
  
Run 'slim prune -py' to see removal options
```

### Node.js Commands

```bash
# Scan current Node.js project
slim scan -node

# Scan with JSON output
slim scan -node --json

# Show unused packages (dry-run)
slim prune -node

# Actually remove unused packages
slim prune -node --force
```

**Example output:**
```
SlimStack Node.js Dependency Scan
===================================
┌──────────────────────────────┐
│           Summary            │
├──────────────────────────────┤
│ Project          :   myapp   │
│ Files Scanned    :       156 │
│ node_modules Size :  245.3 MB │
│ Dependencies     :        32 │
│ Unused Deps      :         8 │
└──────────────────────────────┘

Unused Dependencies:
  - lodash (12.5 MB)
  - moment (4.2 MB)
  - axios (1.8 MB)
```

### Disk Usage Commands

```bash
# Show disk usage by ecosystem
slim disk

# Show disk usage by project
slim disk --by project

# Limit to top 10 results
slim disk --top 10

# Full path scan
slim disk --path /path/to/projects
```

**Example output:**
```
Disk Usage by Ecosystem
─────────────────────────
Python   ████████████████░░░░  1.2 GB
Node.js  ██████████████████░░  2.4 GB
Docker   ████████░░░░░░░░░░░░  856 MB

Python virtual environments:
    245.3 MB  project-a/.venv
    198.7 MB  project-b/venv

Node.js node_modules:
    512.4 MB  app-frontend/node_modules
    324.1 MB  api-server/node_modules
```

### Docker Commands

```bash
# Analyze Dockerfile for security and optimization issues
slim docker

# Output as JSON (for CI/CD)
slim docker --json

# Only show security issues
slim docker --security-only

# Filter by severity (critical, warning, info)
slim docker --severity warning
```

**Example output:**
```text
SlimStack Dockerfile Analysis
================================

Dockerfile: Dockerfile
Base images: 1
Multi-stage: No
Runs as non-root: No
Has HEALTHCHECK: No

Issues Found (4):

  🔴 Line 2: Potential secret exposed in ENV instruction
     Category: security
     → Use Docker secrets or mount secrets at runtime instead of ENV

  🟡 Line 1: Container runs as root (no USER instruction)
     Category: security
     → Add 'USER nonroot' or 'USER 1000' to run as non-root user

Image Recommendations:

  Current:     python:3.12
  Recommended: python:3.12-slim
  Reason:      smaller - Debian slim variant, ~100MB smaller
  Size:        ~150MB

  Current:     python:3.12
  Recommended: cgr.dev/chainguard/python:latest
  Reason:      hardened - Chainguard hardened image, zero CVEs
  Size:        ~50MB

────────────────────────────────
Summary: 1 critical, 2 warnings, 1 info
         2 image recommendations
```

## Safety

SlimStack is designed with safety as a priority:

| Action | Behavior |
|--------|----------|
| `scan` commands | **Read-only** - never modifies anything |
| `prune` commands | **Dry-run by default** - only shows what would be removed |
| `prune --force` | **Requires confirmation** - prompts before deletion |

### Protected Packages

SlimStack will **never** remove:
- `pip`, `setuptools`, `wheel` (Python)
- System Python packages (only operates in virtual environments)
- Global Node packages (only operates on project-local dependencies)

### Virtual Environment Requirement

For Python, SlimStack **requires** running inside a virtual environment for any prune operations. This prevents accidental damage to your system Python installation.

## How It Works

### Python Import Detection

SlimStack uses Python's `ast` module to parse your source files and extract imports:

```python
# Detected imports:
import requests           # Detected
from flask import Flask   # Detected
import os                 # Skipped (stdlib)

# Not detected (logged as "unknown"):
module = __import__(name) # Dynamic import
```

### Node.js Import Detection

SlimStack uses regex patterns to detect JavaScript imports:

```javascript
// Detected imports:
const express = require('express');  // require()
import React from 'react';           // ESM import
import('./dynamic-module');          // Dynamic import

// Not detected (relative paths):
import utils from './utils';         // Local file
```

## JSON Output

All commands support `--json` for CI/CD integration:

```bash
slim scan -py --json > deps.json
```

```json
{
  "project_path": "/path/to/project",
  "in_virtualenv": true,
  "files_scanned": 42,
  "packages": {
    "total": 28,
    "used": ["flask", "requests", "sqlalchemy"],
    "unused": ["black", "isort", "pytest"],
    "transitive_only": []
  },
  "unknown_imports": ["mymodule"]
}
```

## Roadmap

Planned for future releases:

- Transitive dependency analysis
- Requirements.txt / pyproject.toml sync
- Monorepo support
- Cache cleanup (pytest, mypy, ruff)
- Interactive mode (select packages to remove)
- Configuration file support
- Pre-commit hook integration

## Contributing

Contributions are welcome. Please submit a Pull Request.

## License

MIT License - Copyright (c) 2026 arceuzvx
