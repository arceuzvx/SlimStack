"""Tests for slim.scanners.cache_scanner module."""

from pathlib import Path

import pytest

from slim.scanners.cache_scanner import (
    scan_caches,
    clean_caches,
    get_clean_result_dict,
    _categorize,
    _get_dir_size,
    CacheEntry,
    CleanResult,
)


class TestCategorize:
    """Tests for _categorize()."""

    def test_pycache(self):
        assert _categorize("__pycache__") == "python"

    def test_pytest_cache(self):
        assert _categorize(".pytest_cache") == "python"

    def test_mypy_cache(self):
        assert _categorize(".mypy_cache") == "python"

    def test_ruff_cache(self):
        assert _categorize(".ruff_cache") == "python"

    def test_next(self):
        assert _categorize(".next") == "node"

    def test_dist(self):
        assert _categorize("dist") == "build"

    def test_build(self):
        assert _categorize("build") == "build"

    def test_cache(self):
        assert _categorize(".cache") == "node"


class TestGetDirSize:
    """Tests for _get_dir_size()."""

    def test_empty_dir(self, tmp_path):
        d = tmp_path / "empty"
        d.mkdir()
        assert _get_dir_size(d) == 0

    def test_dir_with_files(self, tmp_path):
        d = tmp_path / "data"
        d.mkdir()
        (d / "a.txt").write_text("hello")
        (d / "b.txt").write_text("world")
        size = _get_dir_size(d)
        assert size > 0

    def test_nested_dir(self, tmp_path):
        d = tmp_path / "data" / "sub"
        d.mkdir(parents=True)
        (d / "deep.txt").write_text("x" * 100)
        size = _get_dir_size(tmp_path / "data")
        assert size >= 100


class TestScanCaches:
    """Tests for scan_caches()."""

    def test_finds_pycache(self, tmp_path):
        cache = tmp_path / "project" / "__pycache__"
        cache.mkdir(parents=True)
        (cache / "module.pyc").write_bytes(b"x" * 50)
        result = scan_caches(tmp_path)
        assert len(result.entries) == 1
        assert result.entries[0].category == "python"
        assert result.entries[0].name == "__pycache__"

    def test_finds_pytest_cache(self, tmp_path):
        cache = tmp_path / ".pytest_cache"
        cache.mkdir()
        (cache / "v" / "cache").mkdir(parents=True)
        result = scan_caches(tmp_path)
        names = {e.name for e in result.entries}
        assert ".pytest_cache" in names

    def test_finds_multiple_types(self, tmp_path):
        (tmp_path / "__pycache__").mkdir()
        (tmp_path / ".mypy_cache").mkdir()
        (tmp_path / ".pytest_cache").mkdir()
        result = scan_caches(tmp_path)
        assert len(result.entries) == 3

    def test_skips_venv(self, tmp_path):
        (tmp_path / "venv" / "__pycache__").mkdir(parents=True)
        (tmp_path / "__pycache__").mkdir()
        result = scan_caches(tmp_path)
        # Should only find the top-level __pycache__, not the one in venv
        assert len(result.entries) == 1

    def test_skips_node_modules_but_finds_cache(self, tmp_path):
        nm_cache = tmp_path / "node_modules" / ".cache"
        nm_cache.mkdir(parents=True)
        (nm_cache / "data.json").write_text("{}")
        result = scan_caches(tmp_path)
        names = {e.name for e in result.entries}
        assert "node_modules/.cache" in names

    def test_no_caches(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("pass")
        result = scan_caches(tmp_path)
        assert len(result.entries) == 0
        assert result.total_size == 0

    def test_builds_excluded_by_default(self, tmp_path):
        (tmp_path / "dist").mkdir()
        (tmp_path / "build").mkdir()
        result = scan_caches(tmp_path)
        names = {e.name for e in result.entries}
        assert "dist" not in names
        assert "build" not in names

    def test_builds_included_with_flag(self, tmp_path):
        (tmp_path / "dist").mkdir()
        (tmp_path / "dist" / "bundle.js").write_text("code")
        result = scan_caches(tmp_path, include_builds=True)
        names = {e.name for e in result.entries}
        assert "dist" in names

    def test_total_size_calculated(self, tmp_path):
        cache = tmp_path / "__pycache__"
        cache.mkdir()
        (cache / "data.pyc").write_bytes(b"x" * 200)
        result = scan_caches(tmp_path)
        assert result.total_size >= 200

    def test_sorted_by_size_desc(self, tmp_path):
        big = tmp_path / "__pycache__"
        big.mkdir()
        (big / "big.pyc").write_bytes(b"x" * 1000)
        small = tmp_path / ".pytest_cache"
        small.mkdir()
        (small / "tiny").write_bytes(b"x")
        result = scan_caches(tmp_path)
        assert result.entries[0].size >= result.entries[1].size

    def test_recurses_into_subdirs(self, tmp_path):
        deep = tmp_path / "src" / "pkg" / "__pycache__"
        deep.mkdir(parents=True)
        result = scan_caches(tmp_path)
        assert len(result.entries) == 1

    def test_respects_max_depth(self, tmp_path):
        # Create a deep cache beyond max_depth
        deep = tmp_path
        for i in range(10):
            deep = deep / f"level{i}"
        deep.mkdir(parents=True)
        (deep / "__pycache__").mkdir()
        result = scan_caches(tmp_path, max_depth=3)
        assert len(result.entries) == 0


class TestCleanCaches:
    """Tests for clean_caches()."""

    def test_removes_cache_dirs(self, tmp_path):
        cache = tmp_path / "__pycache__"
        cache.mkdir()
        (cache / "module.pyc").write_bytes(b"x" * 50)
        result = scan_caches(tmp_path)
        clean_caches(result)
        assert not cache.exists()
        assert result.cleaned_count == 1

    def test_selective_clean(self, tmp_path):
        (tmp_path / "__pycache__").mkdir()
        pytest_cache = tmp_path / ".pytest_cache"
        pytest_cache.mkdir()
        result = scan_caches(tmp_path)
        # Only clean the first entry
        clean_caches(result, [result.entries[0]])
        assert result.cleaned_count == 1

    def test_handles_already_deleted(self, tmp_path):
        cache = tmp_path / "__pycache__"
        cache.mkdir()
        result = scan_caches(tmp_path)
        cache.rmdir()  # Remove before clean
        clean_caches(result)
        assert len(result.errors) >= 1


class TestGetCleanResultDict:
    """Tests for get_clean_result_dict()."""

    def test_serializable(self, tmp_path):
        (tmp_path / "__pycache__").mkdir()
        result = scan_caches(tmp_path)
        d = get_clean_result_dict(result)
        assert "entries" in d
        assert "total_size" in d
        assert "summary" in d
        assert isinstance(d["summary"]["by_category"], dict)
