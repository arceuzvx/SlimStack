"""Tests for slim.scanners.deps_parser module."""

import json
from pathlib import Path

import pytest

from slim.scanners.deps_parser import (
    parse_requirements_txt,
    parse_pyproject_toml,
    find_and_parse_declared_deps,
    DeclaredDeps,
)


class TestParseRequirementsTxt:
    """Tests for parse_requirements_txt()."""

    def test_basic_requirements(self, tmp_path):
        req = tmp_path / "requirements.txt"
        req.write_text("flask==2.3.0\nrequests>=2.28\nnumpy\n")
        result = parse_requirements_txt(req)
        assert "flask" in result.dependencies
        assert "requests" in result.dependencies
        assert "numpy" in result.dependencies
        assert result.dependencies["flask"] == "==2.3.0"

    def test_skips_comments(self, tmp_path):
        req = tmp_path / "requirements.txt"
        req.write_text("# comment\nflask\n# another comment\n")
        result = parse_requirements_txt(req)
        assert len(result.dependencies) == 1
        assert "flask" in result.dependencies

    def test_skips_empty_lines(self, tmp_path):
        req = tmp_path / "requirements.txt"
        req.write_text("\nflask\n\nrequests\n\n")
        result = parse_requirements_txt(req)
        assert len(result.dependencies) == 2

    def test_skips_options(self, tmp_path):
        req = tmp_path / "requirements.txt"
        req.write_text("-r base.txt\n--index-url https://pypi.org\nflask\n")
        result = parse_requirements_txt(req)
        assert len(result.dependencies) == 1

    def test_normalizes_names(self, tmp_path):
        req = tmp_path / "requirements.txt"
        req.write_text("scikit-learn>=1.0\nPython-Dateutil\n")
        result = parse_requirements_txt(req)
        assert "scikit_learn" in result.dependencies
        assert "python_dateutil" in result.dependencies

    def test_version_specs(self, tmp_path):
        req = tmp_path / "requirements.txt"
        req.write_text("flask>=2.0,<3.0\nrequests~=2.28\nnumpy!=1.24\n")
        result = parse_requirements_txt(req)
        assert "flask" in result.dependencies
        assert "requests" in result.dependencies
        assert "numpy" in result.dependencies

    def test_missing_file(self, tmp_path):
        result = parse_requirements_txt(tmp_path / "missing.txt")
        assert len(result.errors) > 0
        assert len(result.dependencies) == 0


class TestParsePyprojectToml:
    """Tests for parse_pyproject_toml()."""

    def test_pep621_dependencies(self, tmp_path):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[project]\n'
            'name = "myproject"\n'
            'dependencies = ["flask>=2.3", "requests", "numpy>=1.24"]\n'
        )
        result = parse_pyproject_toml(pyproject)
        assert "flask" in result.dependencies
        assert "requests" in result.dependencies
        assert "numpy" in result.dependencies

    def test_optional_dependencies(self, tmp_path):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[project]\n'
            'name = "myproject"\n'
            'dependencies = ["flask"]\n'
            '\n'
            '[project.optional-dependencies]\n'
            'dev = ["pytest>=7.0", "black"]\n'
            'test = ["coverage"]\n'
        )
        result = parse_pyproject_toml(pyproject)
        assert "flask" in result.dependencies
        assert "pytest" in result.dev_dependencies
        assert "black" in result.dev_dependencies
        assert "coverage" in result.dev_dependencies

    def test_poetry_format(self, tmp_path):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[tool.poetry]\n'
            'name = "myproject"\n'
            '\n'
            '[tool.poetry.dependencies]\n'
            'python = "^3.11"\n'
            'flask = "^2.3"\n'
            'requests = {version = "^2.28", optional = true}\n'
            '\n'
            '[tool.poetry.dev-dependencies]\n'
            'pytest = "^7.0"\n'
        )
        result = parse_pyproject_toml(pyproject)
        assert "flask" in result.dependencies
        assert "requests" in result.dependencies
        assert "python" not in result.dependencies  # skip python itself
        assert "pytest" in result.dev_dependencies

    def test_missing_file(self, tmp_path):
        result = parse_pyproject_toml(tmp_path / "missing.toml")
        assert len(result.errors) > 0

    def test_empty_project(self, tmp_path):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[build-system]\nrequires = ["setuptools"]\n')
        result = parse_pyproject_toml(pyproject)
        assert len(result.dependencies) == 0


class TestFindAndParseDeclaredDeps:
    """Tests for find_and_parse_declared_deps()."""

    def test_prefers_requirements_txt(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("flask\n")
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "x"\ndependencies = ["requests"]\n'
        )
        result = find_and_parse_declared_deps(tmp_path)
        assert result is not None
        assert "flask" in result.dependencies

    def test_falls_back_to_pyproject(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "x"\ndependencies = ["requests"]\n'
        )
        result = find_and_parse_declared_deps(tmp_path)
        assert result is not None
        assert "requests" in result.dependencies

    def test_returns_none_when_no_files(self, tmp_path):
        result = find_and_parse_declared_deps(tmp_path)
        assert result is None
