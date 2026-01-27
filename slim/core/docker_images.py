
"""
Docker image alternatives and hardened image mappings.

Advisory-only: recommendations are heuristic and non-authoritative.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class AlternativeReason(str, Enum):
    HARDENED = "hardened"
    SMALLER = "smaller"
    DISTROLESS = "distroless"
    ALPINE = "alpine"


@dataclass(frozen=True)
class ImageAlternative:
    """A recommended alternative for a base image."""
    image: str
    reason: AlternativeReason
    description: str
    size_estimate: Optional[str] = None  # heuristic only


# -----------------------------
# Static recommendation mapping
# -----------------------------

IMAGE_ALTERNATIVES: dict[str, list[ImageAlternative]] = {
    "python": [
        ImageAlternative(
            image="{name}:{version}-slim",
            reason=AlternativeReason.SMALLER,
            description="Debian slim variant",
            size_estimate="~150MB",
        ),
        ImageAlternative(
            image="{name}:{version}-alpine",
            reason=AlternativeReason.ALPINE,
            description="Alpine Linux base",
            size_estimate="~50MB",
        ),
        ImageAlternative(
            image="cgr.dev/chainguard/python",
            reason=AlternativeReason.HARDENED,
            description="Chainguard hardened, distroless",
            size_estimate="~50MB",
        ),
    ],
    "node": [
        ImageAlternative(
            image="{name}:{version}-slim",
            reason=AlternativeReason.SMALLER,
            description="Debian slim variant",
            size_estimate="~200MB",
        ),
        ImageAlternative(
            image="{name}:{version}-alpine",
            reason=AlternativeReason.ALPINE,
            description="Alpine Linux base",
            size_estimate="~130MB",
        ),
        ImageAlternative(
            image="cgr.dev/chainguard/node",
            reason=AlternativeReason.HARDENED,
            description="Chainguard hardened Node.js",
            size_estimate="~100MB",
        ),
    ],
    "golang": [
        ImageAlternative(
            image="{name}:{version}-alpine",
            reason=AlternativeReason.ALPINE,
            description="Alpine build image",
            size_estimate="~250MB",
        ),
        ImageAlternative(
            image="gcr.io/distroless/static-debian12",
            reason=AlternativeReason.DISTROLESS,
            description="Distroless runtime for static Go binaries",
            size_estimate="~2MB",
        ),
        ImageAlternative(
            image="cgr.dev/chainguard/go",
            reason=AlternativeReason.HARDENED,
            description="Chainguard hardened Go build image",
            size_estimate="~200MB",
        ),
    ],
    "openjdk": [
        ImageAlternative(
            image="eclipse-temurin:{version}-jre-alpine",
            reason=AlternativeReason.ALPINE,
            description="Temurin JRE on Alpine",
            size_estimate="~150MB",
        ),
        ImageAlternative(
            image="gcr.io/distroless/java17-debian12",
            reason=AlternativeReason.DISTROLESS,
            description="Distroless Java runtime",
            size_estimate="~200MB",
        ),
        ImageAlternative(
            image="cgr.dev/chainguard/jre",
            reason=AlternativeReason.HARDENED,
            description="Chainguard hardened JRE",
            size_estimate="~100MB",
        ),
    ],
    "ubuntu": [
        ImageAlternative(
            image="ubuntu:{version}-minimal",
            reason=AlternativeReason.SMALLER,
            description="Ubuntu minimal",
            size_estimate="~30MB",
        ),
        ImageAlternative(
            image="debian:{version}-slim",
            reason=AlternativeReason.SMALLER,
            description="Debian slim",
            size_estimate="~25MB",
        ),
        ImageAlternative(
            image="cgr.dev/chainguard/wolfi-base",
            reason=AlternativeReason.HARDENED,
            description="Wolfi security-focused base",
            size_estimate="~15MB",
        ),
    ],
    "debian": [
        ImageAlternative(
            image="debian:{version}-slim",
            reason=AlternativeReason.SMALLER,
            description="Debian slim",
            size_estimate="~25MB",
        ),
        ImageAlternative(
            image="cgr.dev/chainguard/wolfi-base",
            reason=AlternativeReason.HARDENED,
            description="Wolfi security-focused base",
            size_estimate="~15MB",
        ),
    ],
    "nginx": [
        ImageAlternative(
            image="nginx:{version}-alpine",
            reason=AlternativeReason.ALPINE,
            description="Alpine variant",
            size_estimate="~25MB",
        ),
        ImageAlternative(
            image="cgr.dev/chainguard/nginx",
            reason=AlternativeReason.HARDENED,
            description="Chainguard hardened nginx",
            size_estimate="~15MB",
        ),
    ],
    "redis": [
        ImageAlternative(
            image="redis:{version}-alpine",
            reason=AlternativeReason.ALPINE,
            description="Alpine variant",
            size_estimate="~30MB",
        ),
    ],
    "postgres": [
        ImageAlternative(
            image="postgres:{version}-alpine",
            reason=AlternativeReason.ALPINE,
            description="Alpine variant",
            size_estimate="~80MB",
        ),
    ],
}


# -----------------------------
# Risk & optimization signals
# -----------------------------

RISKY_TAGS = {"latest", "dev", "development", "beta", "rc", "nightly", "unstable"}

HARDENED_REGISTRIES = {
    "cgr.dev/chainguard",
    "gcr.io/distroless",
}

OPTIMIZED_TAG_MARKERS = {"slim", "alpine", "minimal", "distroless"}


# -----------------------------
# Parsing helpers
# -----------------------------

def _strip_digest(image: str) -> str:
    return image.split("@", 1)[0]


def get_base_image_name(image: str) -> str:
    image = _strip_digest(image)
    last_segment = image.rsplit("/", 1)[-1]
    if ":" in last_segment:
        last_segment = last_segment.rsplit(":", 1)[0]
    return last_segment.lower()


def get_image_tag(image: str) -> str:
    image = _strip_digest(image)
    last_segment = image.rsplit("/", 1)[-1]
    if ":" in last_segment:
        return last_segment.rsplit(":", 1)[1]
    return "latest"


def get_image_registry(image: str) -> Optional[str]:
    parts = image.split("/")
    if len(parts) > 1 and "." in parts[0]:
        return parts[0]
    return None


# -----------------------------
# Classification
# -----------------------------

def has_risky_tag(image: str) -> bool:
    if "@" in image:
        return False  # digest-pinned
    return get_image_tag(image).lower() in RISKY_TAGS


def is_hardened_image(image: str) -> bool:
    registry = get_image_registry(image)
    return registry in HARDENED_REGISTRIES


def is_optimized_image(image: str) -> bool:
    tag = get_image_tag(image).lower()
    return any(marker in tag for marker in OPTIMIZED_TAG_MARKERS)


# -----------------------------
# Recommendation engine
# -----------------------------

def _extract_version(tag: str) -> Optional[str]:
    if tag in RISKY_TAGS:
        return None
    return tag.split("-", 1)[0]


def get_alternatives(image: str) -> list[ImageAlternative]:
    base_name = get_base_image_name(image)
    tag = get_image_tag(image).lower()
    version = _extract_version(tag)

    alternatives = IMAGE_ALTERNATIVES.get(base_name, [])
    results: list[ImageAlternative] = []

    for alt in alternatives:
        if "{version}" in alt.image and not version:
            continue

        formatted = (
            alt.image.format(name=base_name, version=version)
            if "{version}" in alt.image
            else alt.image
        )

        # Do not recommend the same image
        if formatted == image:
            continue

        results.append(alt)

    return results
