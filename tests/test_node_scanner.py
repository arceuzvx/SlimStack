"""Tests for slim.scanners.node_scanner module."""

import json
import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest

from slim.scanners.node_scanner import (
    get_package_name,
    parse_package_json,
    extract_imports_from_file,
    find_js_files,
    NodePackageInfo,
    NodeImportInfo,
)


class TestGetPackageName:
    """Tests for get_package_name()."""

    def test_simple_package(self):
        assert get_package_name("lodash") == "lodash"

    def test_package_with_subpath(self):
        assert get_package_name("lodash/get") == "lodash"

    def test_scoped_package(self):
        assert get_package_name("@angular/core") == "@angular/core"

    def test_scoped_package_with_subpath(self):
        assert get_package_name("@angular/core/testing") == "@angular/core"

    def test_relative_import_returns_none(self):
        assert get_package_name("./utils") is None

    def test_parent_relative_returns_none(self):
        assert get_package_name("../lib/helper") is None

    def test_absolute_path_returns_none(self):
        assert get_package_name("/absolute/path") is None

    def test_node_builtin_returns_none(self):
        assert get_package_name("fs") is None
        assert get_package_name("path") is None
        assert get_package_name("http") is None

    def test_node_prefixed_builtin_returns_none(self):
        assert get_package_name("node:fs") is None
        assert get_package_name("node:path") is None

    def test_scope_only(self):
        result = get_package_name("@types")
        assert result == "@types"


class TestParsePackageJson:
    """Tests for parse_package_json()."""

    def test_basic_deps(self, tmp_path):
        pkg = tmp_path / "package.json"
        pkg.write_text(json.dumps({
            "dependencies": {"express": "^4.18.0", "lodash": "^4.17.0"},
            "devDependencies": {"jest": "^29.0.0"},
        }))
        deps, dev_deps = parse_package_json(pkg)
        assert "express" in deps
        assert "lodash" in deps
        assert "jest" in dev_deps
        assert deps["express"].version == "^4.18.0"
        assert dev_deps["jest"].is_dev is True

    def test_no_deps(self, tmp_path):
        pkg = tmp_path / "package.json"
        pkg.write_text(json.dumps({"name": "empty"}))
        deps, dev_deps = parse_package_json(pkg)
        assert len(deps) == 0
        assert len(dev_deps) == 0

    def test_invalid_json(self, tmp_path):
        pkg = tmp_path / "package.json"
        pkg.write_text("{{invalid json}}")
        deps, dev_deps = parse_package_json(pkg)
        assert len(deps) == 0
        assert len(dev_deps) == 0

    def test_missing_file(self, tmp_path):
        pkg = tmp_path / "nonexistent.json"
        deps, dev_deps = parse_package_json(pkg)
        assert len(deps) == 0


class TestExtractImportsFromFile:
    """Tests for Node.js extract_imports_from_file()."""

    def test_require(self, tmp_path):
        f = tmp_path / "app.js"
        f.write_text("const express = require('express');\n")
        imports = list(extract_imports_from_file(f))
        module_names = [imp.module_name for imp in imports]
        assert "express" in module_names

    def test_esm_import(self, tmp_path):
        f = tmp_path / "app.mjs"
        f.write_text("import React from 'react';\n")
        imports = list(extract_imports_from_file(f))
        module_names = [imp.module_name for imp in imports]
        assert "react" in module_names

    def test_named_import(self, tmp_path):
        f = tmp_path / "app.js"
        f.write_text("import { useState } from 'react';\n")
        imports = list(extract_imports_from_file(f))
        module_names = [imp.module_name for imp in imports]
        assert "react" in module_names

    def test_dynamic_import(self, tmp_path):
        f = tmp_path / "app.js"
        f.write_text("const mod = import('lodash');\n")
        imports = list(extract_imports_from_file(f))
        module_names = [imp.module_name for imp in imports]
        assert "lodash" in module_names

    def test_relative_import_included_raw(self, tmp_path):
        f = tmp_path / "app.js"
        f.write_text("import utils from './utils';\n")
        imports = list(extract_imports_from_file(f))
        # Relative imports are detected but filtered by get_package_name
        module_names = [imp.module_name for imp in imports]
        assert "./utils" in module_names

    def test_multiple_imports(self, tmp_path):
        f = tmp_path / "app.js"
        f.write_text(textwrap.dedent("""\
            const express = require('express');
            import React from 'react';
            import { Router } from 'vue-router';
        """))
        imports = list(extract_imports_from_file(f))
        module_names = [imp.module_name for imp in imports]
        assert "express" in module_names
        assert "react" in module_names
        assert "vue-router" in module_names


class TestFindJsFiles:
    """Tests for find_js_files()."""

    def test_finds_js_files(self, tmp_path):
        (tmp_path / "app.js").write_text("// app")
        (tmp_path / "util.ts").write_text("// util")
        (tmp_path / "readme.md").write_text("# readme")
        found = list(find_js_files(tmp_path))
        assert len(found) == 2

    def test_finds_all_extensions(self, tmp_path):
        for ext in [".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts"]:
            (tmp_path / f"file{ext}").write_text("// code")
        found = list(find_js_files(tmp_path))
        assert len(found) == 8

    def test_skips_node_modules(self, tmp_path):
        nm = tmp_path / "node_modules" / "express"
        nm.mkdir(parents=True)
        (nm / "index.js").write_text("// express")
        (tmp_path / "app.js").write_text("// app")
        found = list(find_js_files(tmp_path))
        assert len(found) == 1

    def test_skips_hidden_dirs(self, tmp_path):
        hidden = tmp_path / ".next"
        hidden.mkdir()
        (hidden / "build.js").write_text("// build")
        found = list(find_js_files(tmp_path))
        assert len(found) == 0

    def test_recurses_into_src(self, tmp_path):
        src = tmp_path / "src" / "components"
        src.mkdir(parents=True)
        (src / "Button.tsx").write_text("// button")
        found = list(find_js_files(tmp_path))
        assert len(found) == 1
