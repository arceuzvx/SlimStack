"""Tests for slim.scanners.python_scanner module."""

import ast
import textwrap
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from slim.scanners.python_scanner import (
    normalize_package_name,
    get_top_level_module,
    extract_imports_from_file,
    map_import_to_package,
    find_python_files,
    get_stdlib_modules,
    PackageInfo,
    ImportInfo,
)


class TestNormalizePackageName:
    """Tests for normalize_package_name()."""

    def test_lowercase(self):
        assert normalize_package_name("Flask") == "flask"

    def test_hyphens_to_underscores(self):
        assert normalize_package_name("scikit-learn") == "scikit_learn"

    def test_dots_to_underscores(self):
        assert normalize_package_name("zope.interface") == "zope_interface"

    def test_mixed(self):
        assert normalize_package_name("My-Package.Name") == "my_package_name"

    def test_already_normalized(self):
        assert normalize_package_name("requests") == "requests"


class TestGetTopLevelModule:
    """Tests for get_top_level_module()."""

    def test_simple_module(self):
        assert get_top_level_module("requests") == "requests"

    def test_dotted_import(self):
        assert get_top_level_module("flask.views") == "flask"

    def test_deeply_nested(self):
        assert get_top_level_module("a.b.c.d") == "a"


class TestExtractImportsFromFile:
    """Tests for extract_imports_from_file()."""

    def test_simple_import(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("import requests\n", encoding="utf-8")
        imports = list(extract_imports_from_file(f))
        assert len(imports) == 1
        assert imports[0].module_name == "requests"
        assert imports[0].is_from_import is False

    def test_from_import(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("from flask import Flask\n", encoding="utf-8")
        imports = list(extract_imports_from_file(f))
        assert len(imports) == 1
        assert imports[0].module_name == "flask"
        assert imports[0].is_from_import is True

    def test_multiple_imports(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text(textwrap.dedent("""\
            import os
            import requests
            from flask import Flask
            from pathlib import Path
        """), encoding="utf-8")
        imports = list(extract_imports_from_file(f))
        module_names = {imp.module_name for imp in imports}
        assert "os" in module_names
        assert "requests" in module_names
        assert "flask" in module_names
        assert "pathlib" in module_names

    def test_relative_import_skipped(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("from . import utils\n", encoding="utf-8")
        imports = list(extract_imports_from_file(f))
        # Relative imports should be skipped (no module_name)
        assert len(imports) == 0

    def test_syntax_error_handled(self, tmp_path):
        f = tmp_path / "bad.py"
        f.write_text("def broken(\n", encoding="utf-8")
        imports = list(extract_imports_from_file(f))
        assert len(imports) == 0

    def test_import_line_numbers(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("# comment\nimport flask\n", encoding="utf-8")
        imports = list(extract_imports_from_file(f))
        assert imports[0].line_number == 2

    def test_aliased_import(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("import numpy as np\n", encoding="utf-8")
        imports = list(extract_imports_from_file(f))
        assert imports[0].module_name == "numpy"


class TestMapImportToPackage:
    """Tests for map_import_to_package()."""

    def _make_packages(self, names: list[str]) -> dict[str, PackageInfo]:
        return {
            normalize_package_name(n): PackageInfo(name=n, version="1.0")
            for n in names
        }

    def test_direct_match(self):
        pkgs = self._make_packages(["requests"])
        assert map_import_to_package("requests", pkgs) == "requests"

    def test_known_mapping_pil(self):
        pkgs = self._make_packages(["Pillow"])
        assert map_import_to_package("PIL", pkgs) == "pillow"

    def test_known_mapping_yaml(self):
        pkgs = self._make_packages(["PyYAML"])
        assert map_import_to_package("yaml", pkgs) == "pyyaml"

    def test_known_mapping_sklearn(self):
        pkgs = self._make_packages(["scikit-learn"])
        assert map_import_to_package("sklearn", pkgs) == "scikit_learn"

    def test_known_mapping_cv2(self):
        pkgs = self._make_packages(["opencv-python"])
        assert map_import_to_package("cv2", pkgs) == "opencv_python"

    def test_known_mapping_dotenv(self):
        pkgs = self._make_packages(["python-dotenv"])
        assert map_import_to_package("dotenv", pkgs) == "python_dotenv"

    def test_unknown_import(self):
        pkgs = self._make_packages(["requests"])
        assert map_import_to_package("nonexistent_module", pkgs) is None

    def test_python_prefix_variation(self):
        pkgs = self._make_packages(["python_magic"])
        result = map_import_to_package("magic", pkgs)
        # Should find via known mapping or variation
        assert result == "python_magic"


class TestFindPythonFiles:
    """Tests for find_python_files()."""

    def test_finds_py_files(self, tmp_path):
        (tmp_path / "main.py").write_text("pass")
        (tmp_path / "util.py").write_text("pass")
        (tmp_path / "readme.md").write_text("# readme")
        found = list(find_python_files(tmp_path))
        assert len(found) == 2
        assert all(f.suffix == ".py" for f in found)

    def test_skips_pycache(self, tmp_path):
        cache = tmp_path / "__pycache__"
        cache.mkdir()
        (cache / "cached.py").write_text("pass")
        (tmp_path / "main.py").write_text("pass")
        found = list(find_python_files(tmp_path))
        assert len(found) == 1

    def test_skips_venv(self, tmp_path):
        venv = tmp_path / "venv"
        venv.mkdir()
        (venv / "activate.py").write_text("pass")
        (tmp_path / "app.py").write_text("pass")
        found = list(find_python_files(tmp_path))
        assert len(found) == 1

    def test_recurses_into_subdirs(self, tmp_path):
        sub = tmp_path / "src" / "pkg"
        sub.mkdir(parents=True)
        (sub / "module.py").write_text("pass")
        found = list(find_python_files(tmp_path))
        assert len(found) == 1

    def test_skips_hidden_dirs(self, tmp_path):
        hidden = tmp_path / ".hidden"
        hidden.mkdir()
        (hidden / "secret.py").write_text("pass")
        found = list(find_python_files(tmp_path))
        assert len(found) == 0


class TestGetStdlibModules:
    """Tests for get_stdlib_modules()."""

    def test_returns_frozenset(self):
        result = get_stdlib_modules()
        assert isinstance(result, frozenset)

    def test_contains_common_modules(self):
        result = get_stdlib_modules()
        assert "os" in result
        assert "sys" in result
        assert "json" in result
        assert "pathlib" in result
