"""Tests for slim.scanners.docker_scanner module."""

import textwrap
from pathlib import Path

import pytest

from slim.scanners.docker_scanner import (
    parse_dockerfile,
    analyze_dockerfile,
    find_dockerfile,
    scan_dockerfile,
    DockerfileIssue,
    DockerScanResult,
)


class TestParseDockerfile:
    """Tests for parse_dockerfile()."""

    def test_basic_parse(self, tmp_path):
        df = tmp_path / "Dockerfile"
        df.write_text("FROM python:3.12\nRUN pip install flask\n")
        lines = parse_dockerfile(df)
        assert len(lines) == 2
        assert lines[0] == (1, "FROM python:3.12")
        assert lines[1] == (2, "RUN pip install flask")

    def test_empty_file(self, tmp_path):
        df = tmp_path / "Dockerfile"
        df.write_text("")
        lines = parse_dockerfile(df)
        assert len(lines) == 0

    def test_with_comments(self, tmp_path):
        df = tmp_path / "Dockerfile"
        df.write_text("# comment\nFROM node:18\n# another comment\nRUN npm install\n")
        lines = parse_dockerfile(df)
        assert len(lines) == 4


class TestAnalyzeDockerfile:
    """Tests for analyze_dockerfile()."""

    def _make_lines(self, content: str) -> list[tuple[int, str]]:
        """Helper to create numbered lines from content string."""
        return [(i, line) for i, line in enumerate(content.splitlines(), 1)]

    def test_detects_base_image(self):
        lines = self._make_lines("FROM python:3.12\nRUN pip install flask")
        result = analyze_dockerfile(lines)
        assert len(result.base_images) == 1
        assert result.base_images[0][1] == "python:3.12"

    def test_detects_multi_stage(self):
        lines = self._make_lines(
            "FROM python:3.12 AS builder\nRUN pip install flask\nFROM python:3.12-slim\nCOPY --from=builder /app /app"
        )
        result = analyze_dockerfile(lines)
        assert result.multi_stage is True
        assert result.stage_count == 2

    def test_detects_no_user(self):
        lines = self._make_lines("FROM python:3.12\nRUN pip install flask")
        result = analyze_dockerfile(lines)
        assert result.has_user_instruction is False
        # Should have a warning about running as root
        root_issues = [i for i in result.issues if "root" in i.message.lower()]
        assert len(root_issues) == 1

    def test_detects_user_instruction(self):
        lines = self._make_lines("FROM python:3.12\nUSER nonroot\nRUN pip install flask")
        result = analyze_dockerfile(lines)
        assert result.has_user_instruction is True
        root_issues = [i for i in result.issues if "root" in i.message.lower()]
        assert len(root_issues) == 0

    def test_detects_no_healthcheck(self):
        lines = self._make_lines("FROM python:3.12\nRUN pip install flask")
        result = analyze_dockerfile(lines)
        assert result.has_healthcheck is False
        hc_issues = [i for i in result.issues if "HEALTHCHECK" in i.message]
        assert len(hc_issues) == 1

    def test_detects_healthcheck(self):
        lines = self._make_lines("FROM python:3.12\nHEALTHCHECK CMD curl -f http://localhost/")
        result = analyze_dockerfile(lines)
        assert result.has_healthcheck is True

    def test_detects_secret_in_env(self):
        lines = self._make_lines("FROM python:3.12\nENV DATABASE_PASSWORD=mysecret")
        result = analyze_dockerfile(lines)
        secret_issues = [i for i in result.issues if i.category == "security" and "secret" in i.message.lower()]
        assert len(secret_issues) >= 1
        assert secret_issues[0].severity == "critical"

    def test_detects_secret_in_arg(self):
        lines = self._make_lines("FROM python:3.12\nARG API_KEY")
        result = analyze_dockerfile(lines)
        arg_issues = [i for i in result.issues if "ARG" in i.message]
        assert len(arg_issues) >= 1

    def test_detects_risky_tag(self):
        lines = self._make_lines("FROM python:latest")
        result = analyze_dockerfile(lines)
        tag_issues = [i for i in result.issues if "unpinned" in i.message.lower() or "latest" in i.message.lower()]
        assert len(tag_issues) >= 1

    def test_pinned_tag_no_warning(self):
        lines = self._make_lines("FROM python:3.12")
        result = analyze_dockerfile(lines)
        tag_issues = [i for i in result.issues if "unpinned" in i.message.lower()]
        assert len(tag_issues) == 0

    def test_detects_add_for_local_files(self):
        lines = self._make_lines("FROM python:3.12\nADD requirements.txt /app/")
        result = analyze_dockerfile(lines)
        add_issues = [i for i in result.issues if "ADD" in i.message]
        assert len(add_issues) >= 1

    def test_add_url_not_flagged(self):
        lines = self._make_lines("FROM python:3.12\nADD https://example.com/file.tar.gz /app/")
        result = analyze_dockerfile(lines)
        add_issues = [i for i in result.issues if "ADD" in i.message and "local" in i.message.lower()]
        assert len(add_issues) == 0

    def test_detects_copy_dot_dot(self):
        lines = self._make_lines("FROM python:3.12\nCOPY . .")
        result = analyze_dockerfile(lines)
        copy_issues = [i for i in result.issues if "COPY . ." in i.message]
        assert len(copy_issues) >= 1

    def test_detects_pip_no_cache(self):
        lines = self._make_lines("FROM python:3.12\nRUN pip install flask")
        result = analyze_dockerfile(lines)
        pip_issues = [i for i in result.issues if "pip" in i.message.lower() and "cache" in i.message.lower()]
        assert len(pip_issues) >= 1

    def test_pip_with_cache_ok(self):
        lines = self._make_lines("FROM python:3.12\nRUN pip install --no-cache-dir flask")
        result = analyze_dockerfile(lines)
        pip_issues = [i for i in result.issues if "pip" in i.message.lower() and "cache" in i.message.lower()]
        assert len(pip_issues) == 0

    def test_suggests_multi_stage_for_build_images(self):
        lines = self._make_lines("FROM golang:1.21\nRUN go build -o /app .")
        result = analyze_dockerfile(lines)
        ms_issues = [i for i in result.issues if "multi-stage" in i.message.lower()]
        assert len(ms_issues) >= 1

    def test_issues_sorted_by_severity(self):
        lines = self._make_lines(
            "FROM python:latest\nENV DB_PASSWORD=secret\nCOPY . .\nRUN pip install flask"
        )
        result = analyze_dockerfile(lines)
        severities = [i.severity for i in result.issues]
        order = {"critical": 0, "warning": 1, "info": 2}
        for i in range(len(severities) - 1):
            assert order.get(severities[i], 3) <= order.get(severities[i + 1], 3)

    def test_generates_recommendations(self):
        lines = self._make_lines("FROM python:3.12\nRUN pip install flask")
        result = analyze_dockerfile(lines)
        assert len(result.recommendations) > 0

    def test_comments_and_empty_lines_skipped(self):
        lines = self._make_lines("# header\n\nFROM python:3.12\n# comment\nRUN echo ok")
        result = analyze_dockerfile(lines)
        assert len(result.base_images) == 1


class TestFindDockerfile:
    """Tests for find_dockerfile()."""

    def test_finds_standard_dockerfile(self, tmp_path):
        (tmp_path / "Dockerfile").write_text("FROM python:3.12")
        result = find_dockerfile(tmp_path)
        assert result is not None
        assert result.name == "Dockerfile"

    def test_finds_prod_variant(self, tmp_path):
        (tmp_path / "Dockerfile.prod").write_text("FROM python:3.12-slim")
        result = find_dockerfile(tmp_path)
        assert result is not None

    def test_returns_none_when_missing(self, tmp_path):
        result = find_dockerfile(tmp_path)
        assert result is None

    def test_prefers_standard_name(self, tmp_path):
        (tmp_path / "Dockerfile").write_text("FROM python:3.12")
        (tmp_path / "Dockerfile.dev").write_text("FROM python:3.12")
        result = find_dockerfile(tmp_path)
        assert result.name == "Dockerfile"


class TestScanDockerfile:
    """Tests for the top-level scan_dockerfile()."""

    def test_scan_with_dockerfile(self, tmp_path):
        df = tmp_path / "Dockerfile"
        df.write_text("FROM python:3.12\nRUN pip install flask\n")
        result = scan_dockerfile(project_path=tmp_path)
        assert len(result.base_images) == 1
        assert result.dockerfile_path == df

    def test_scan_no_dockerfile(self, tmp_path):
        result = scan_dockerfile(project_path=tmp_path)
        assert len(result.issues) == 1
        assert result.issues[0].message == "No Dockerfile found"

    def test_scan_direct_path(self, tmp_path):
        df = tmp_path / "custom.Dockerfile"
        df.write_text("FROM node:18\nUSER node\nHEALTHCHECK CMD curl http://localhost/\n")
        result = scan_dockerfile(dockerfile_path=df)
        assert result.has_user_instruction is True
        assert result.has_healthcheck is True

    def test_result_to_dict(self, tmp_path):
        df = tmp_path / "Dockerfile"
        df.write_text("FROM python:3.12\n")
        result = scan_dockerfile(project_path=tmp_path)
        d = result.to_dict()
        assert "issues" in d
        assert "recommendations" in d
        assert "summary" in d
        assert isinstance(d["summary"]["total_issues"], int)
