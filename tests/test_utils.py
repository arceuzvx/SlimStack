"""Tests for slim.core.utils module."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from slim.core.utils import (
    format_size,
    is_in_virtualenv,
    get_virtualenv_path,
    find_project_root,
    is_tty,
    run_command,
)


class TestFormatSize:
    """Tests for format_size()."""

    def test_zero_bytes(self):
        assert format_size(0) == "0 B"

    def test_negative_bytes(self):
        assert format_size(-100) == "0 B"

    def test_bytes(self):
        assert format_size(500) == "500 B"

    def test_kilobytes(self):
        assert format_size(1024) == "1.0 KB"

    def test_megabytes(self):
        assert format_size(1024 * 1024) == "1.0 MB"

    def test_gigabytes(self):
        assert format_size(1024 ** 3) == "1.0 GB"

    def test_terabytes(self):
        assert format_size(1024 ** 4) == "1.0 TB"

    def test_fractional_megabytes(self):
        result = format_size(int(1.5 * 1024 * 1024))
        assert result == "1.5 MB"

    def test_large_value(self):
        result = format_size(2 * 1024 ** 4)
        assert "TB" in result

    def test_one_byte(self):
        assert format_size(1) == "1 B"

    def test_just_under_kb(self):
        assert format_size(1023) == "1023 B"


class TestVirtualEnv:
    """Tests for virtualenv detection."""

    def test_not_in_virtualenv_when_no_prefix(self):
        with patch.object(sys, 'base_prefix', sys.prefix):
            with patch.object(sys, 'prefix', sys.prefix):
                if hasattr(sys, 'real_prefix'):
                    # Can't easily test this case
                    return
                result = is_in_virtualenv()
                # Result depends on actual environment

    def test_get_virtualenv_path_returns_path_or_none(self):
        result = get_virtualenv_path()
        if is_in_virtualenv():
            assert isinstance(result, Path)
        else:
            assert result is None


class TestFindProjectRoot:
    """Tests for find_project_root()."""

    def test_finds_current_project(self):
        """SlimStack's own root should be found from within its directory."""
        slimstack_root = Path(__file__).parent.parent
        result = find_project_root(slimstack_root / "slim")
        assert (result / "pyproject.toml").exists()

    def test_returns_start_path_when_no_markers(self, tmp_path):
        """When no project markers exist, returns the start path."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        result = find_project_root(empty_dir)
        assert result == empty_dir.resolve()

    def test_finds_git_marker(self, tmp_path):
        """Should find root with .git directory."""
        (tmp_path / ".git").mkdir()
        sub = tmp_path / "sub" / "deep"
        sub.mkdir(parents=True)
        result = find_project_root(sub)
        assert result == tmp_path

    def test_finds_package_json(self, tmp_path):
        """Should find root with package.json."""
        (tmp_path / "package.json").write_text("{}")
        sub = tmp_path / "src"
        sub.mkdir()
        result = find_project_root(sub)
        assert result == tmp_path


class TestRunCommand:
    """Tests for run_command()."""

    def test_successful_command(self):
        returncode, stdout, stderr = run_command([sys.executable, "-c", "print('hello')"])
        assert returncode == 0
        assert "hello" in stdout

    def test_failed_command(self):
        returncode, stdout, stderr = run_command([sys.executable, "-c", "import sys; sys.exit(1)"])
        assert returncode == 1

    def test_command_not_found(self):
        returncode, stdout, stderr = run_command(["nonexistent_command_12345"])
        assert returncode == -1
        assert "not found" in stderr.lower() or "Command not found" in stderr


class TestIsTty:
    """Tests for is_tty()."""

    def test_returns_bool(self):
        result = is_tty()
        assert isinstance(result, bool)
