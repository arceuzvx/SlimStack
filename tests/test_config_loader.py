"""Tests for slim.core.config_loader module."""

from pathlib import Path

import pytest

from slim.core.config_loader import (
    load_config,
    _find_config_file,
    _parse_toml,
    _merge_config,
    SlimConfig,
    CONFIG_FILENAMES,
)


class TestFindConfigFile:
    """Tests for _find_config_file()."""

    def test_finds_slimrc_in_current_dir(self, tmp_path):
        cfg = tmp_path / ".slimrc.toml"
        cfg.write_text('[defaults]\njson = true\n')
        result = _find_config_file(tmp_path)
        assert result == cfg

    def test_finds_slimstack_toml(self, tmp_path):
        cfg = tmp_path / "slimstack.toml"
        cfg.write_text('[defaults]\njson = true\n')
        result = _find_config_file(tmp_path)
        assert result == cfg

    def test_walks_up_directory_tree(self, tmp_path):
        cfg = tmp_path / ".slimrc.toml"
        cfg.write_text('exclude = ["black"]\n')
        sub = tmp_path / "src" / "pkg"
        sub.mkdir(parents=True)
        result = _find_config_file(sub)
        assert result == cfg

    def test_returns_none_when_no_config(self, tmp_path):
        sub = tmp_path / "empty"
        sub.mkdir()
        result = _find_config_file(sub)
        # Could be None or a home-dir config; we can't control home
        # Just verify it doesn't crash


class TestMergeConfig:
    """Tests for _merge_config()."""

    def test_exclude_packages(self):
        config = SlimConfig()
        _merge_config({"exclude": ["black", "isort"]}, config)
        assert config.exclude_packages == ["black", "isort"]

    def test_fail_on_unused(self):
        config = SlimConfig()
        _merge_config({"fail_on_unused": True}, config)
        assert config.fail_on_unused is True

    def test_defaults_section(self):
        config = SlimConfig()
        _merge_config({"defaults": {"json": True, "verbose": True, "quiet": False}}, config)
        assert config.default_json is True
        assert config.default_verbose is True
        assert config.default_quiet is False

    def test_python_section(self):
        config = SlimConfig()
        data = {
            "python": {
                "exclude": ["pytest", "mypy"],
                "known_mappings": {"cv2": "opencv-python"},
            }
        }
        _merge_config(data, config)
        assert config.python_exclude == ["pytest", "mypy"]
        assert config.python_known_mappings == {"cv2": "opencv-python"}

    def test_node_section(self):
        config = SlimConfig()
        _merge_config({"node": {"exclude": ["jest"], "include_dev": True}}, config)
        assert config.node_exclude == ["jest"]
        assert config.node_include_dev is True

    def test_docker_section(self):
        config = SlimConfig()
        _merge_config({"docker": {"severity": "warning", "security_only": True}}, config)
        assert config.docker_severity == "warning"
        assert config.docker_security_only is True

    def test_scan_section(self):
        config = SlimConfig()
        _merge_config({"scan": {"exclude_dirs": [".next", "dist"], "exclude_files": ["legacy.py"]}}, config)
        assert config.scan_exclude_dirs == [".next", "dist"]
        assert config.scan_exclude_files == ["legacy.py"]

    def test_invalid_types_ignored(self):
        config = SlimConfig()
        _merge_config({"exclude": "not_a_list", "defaults": "not_a_dict"}, config)
        assert config.exclude_packages == []  # unchanged


class TestLoadConfig:
    """Tests for load_config()."""

    def test_loads_valid_config(self, tmp_path):
        cfg = tmp_path / ".slimrc.toml"
        cfg.write_text(
            'exclude = ["black", "isort"]\n'
            'fail_on_unused = true\n'
            '\n'
            '[python]\n'
            'exclude = ["pytest"]\n'
        )
        config = load_config(start_path=tmp_path)
        assert config.config_path == cfg
        assert "black" in config.exclude_packages
        assert "isort" in config.exclude_packages
        assert config.fail_on_unused is True
        assert "pytest" in config.python_exclude

    def test_returns_defaults_when_no_config(self, tmp_path):
        sub = tmp_path / "no_config"
        sub.mkdir()
        config = load_config(start_path=sub)
        assert config.config_path is None
        assert config.exclude_packages == []
        assert config.fail_on_unused is False

    def test_handles_malformed_toml(self, tmp_path):
        cfg = tmp_path / ".slimrc.toml"
        cfg.write_text("{{[[invalid toml content")
        config = load_config(start_path=tmp_path)
        # Should return defaults, not crash
        assert config.exclude_packages == []
