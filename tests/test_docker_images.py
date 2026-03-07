"""Tests for slim.core.docker_images module."""

import pytest

from slim.core.docker_images import (
    get_base_image_name,
    get_image_tag,
    get_image_registry,
    has_risky_tag,
    is_hardened_image,
    is_optimized_image,
    is_already_optimized,
    get_alternatives,
    ImageAlternative,
    AlternativeReason,
)


class TestGetBaseImageName:
    """Tests for get_base_image_name()."""

    def test_simple_image(self):
        assert get_base_image_name("python") == "python"

    def test_image_with_tag(self):
        assert get_base_image_name("python:3.12") == "python"

    def test_image_with_registry(self):
        assert get_base_image_name("docker.io/library/python:3.12") == "python"

    def test_image_with_digest(self):
        assert get_base_image_name("python@sha256:abc123") == "python"

    def test_chainguard_image(self):
        assert get_base_image_name("cgr.dev/chainguard/python:latest") == "python"

    def test_image_name_lowercase(self):
        assert get_base_image_name("Python:3.12") == "python"

    def test_scoped_image(self):
        assert get_base_image_name("gcr.io/distroless/static-debian12") == "static-debian12"


class TestGetImageTag:
    """Tests for get_image_tag()."""

    def test_explicit_tag(self):
        assert get_image_tag("python:3.12") == "3.12"

    def test_no_tag_defaults_latest(self):
        assert get_image_tag("python") == "latest"

    def test_tag_with_variant(self):
        assert get_image_tag("python:3.12-slim") == "3.12-slim"

    def test_digest_stripped(self):
        assert get_image_tag("python:3.12@sha256:abc") == "3.12"

    def test_no_tag_with_digest(self):
        assert get_image_tag("python@sha256:abc") == "latest"


class TestGetImageRegistry:
    """Tests for get_image_registry()."""

    def test_no_registry(self):
        assert get_image_registry("python:3.12") is None

    def test_docker_hub(self):
        assert get_image_registry("docker.io/library/python") == "docker.io"

    def test_chainguard(self):
        assert get_image_registry("cgr.dev/chainguard/python") == "cgr.dev"

    def test_gcr(self):
        assert get_image_registry("gcr.io/distroless/static") == "gcr.io"

    def test_no_dot_in_first_segment(self):
        # e.g. "library/python" — "library" is not a registry
        assert get_image_registry("library/python") is None


class TestHasRiskyTag:
    """Tests for has_risky_tag()."""

    def test_latest_is_risky(self):
        assert has_risky_tag("python:latest") is True

    def test_no_tag_is_risky(self):
        # No tag defaults to "latest"
        assert has_risky_tag("python") is True

    def test_dev_is_risky(self):
        assert has_risky_tag("node:dev") is True

    def test_pinned_version_not_risky(self):
        assert has_risky_tag("python:3.12") is False

    def test_digest_pinned_not_risky(self):
        assert has_risky_tag("python@sha256:abc123") is False

    def test_beta_is_risky(self):
        assert has_risky_tag("node:beta") is True

    def test_slim_not_risky(self):
        assert has_risky_tag("python:3.12-slim") is False


class TestIsHardenedImage:
    """Tests for is_hardened_image()."""

    def test_chainguard_is_hardened(self):
        assert is_hardened_image("cgr.dev/chainguard/python:latest") is True

    def test_distroless_is_hardened(self):
        assert is_hardened_image("gcr.io/distroless/static-debian12") is True

    def test_regular_image_not_hardened(self):
        assert is_hardened_image("python:3.12") is False

    def test_alpine_not_hardened(self):
        assert is_hardened_image("python:3.12-alpine") is False


class TestIsOptimizedImage:
    """Tests for is_optimized_image()."""

    def test_slim_is_optimized(self):
        assert is_optimized_image("python:3.12-slim") is True

    def test_alpine_is_optimized(self):
        assert is_optimized_image("python:3.12-alpine") is True

    def test_regular_not_optimized(self):
        assert is_optimized_image("python:3.12") is False

    def test_latest_not_optimized(self):
        assert is_optimized_image("python:latest") is False


class TestIsAlreadyOptimized:
    """Tests for is_already_optimized()."""

    def test_slim_is_already_optimized(self):
        assert is_already_optimized("python:3.12-slim") is True

    def test_hardened_is_already_optimized(self):
        assert is_already_optimized("cgr.dev/chainguard/python:latest") is True

    def test_regular_not_already_optimized(self):
        assert is_already_optimized("python:3.12") is False

    def test_alpine_is_already_optimized(self):
        assert is_already_optimized("node:18-alpine") is True


class TestGetAlternatives:
    """Tests for get_alternatives()."""

    def test_python_has_alternatives(self):
        alts = get_alternatives("python:3.12")
        assert len(alts) > 0
        assert all(isinstance(a, ImageAlternative) for a in alts)

    def test_node_has_alternatives(self):
        alts = get_alternatives("node:18")
        assert len(alts) > 0

    def test_unknown_image_no_alternatives(self):
        alts = get_alternatives("my-custom-image:v1")
        assert len(alts) == 0

    def test_already_optimized_still_returns(self):
        # get_alternatives doesn't filter by optimization, the scanner does
        alts = get_alternatives("python:3.12")
        reasons = {a.reason for a in alts}
        assert AlternativeReason.SMALLER in reasons or AlternativeReason.ALPINE in reasons

    def test_golang_has_distroless(self):
        alts = get_alternatives("golang:1.21")
        reasons = {a.reason for a in alts}
        assert AlternativeReason.DISTROLESS in reasons

    def test_no_version_skips_versioned_alternatives(self):
        alts = get_alternatives("python:latest")
        # Alternatives with {version} template should be skipped for "latest"
        for alt in alts:
            assert "{version}" not in alt.image
