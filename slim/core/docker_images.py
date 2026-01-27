"""Docker image alternatives and hardened image mappings."""

from dataclasses import dataclass


@dataclass
class ImageAlternative:
    """A recommended alternative for a base image."""
    image: str
    reason: str  # "hardened", "smaller", "distroless", "alpine"
    description: str
    size_estimate: str | None = None  # e.g., "~50MB" or "~800MB savings"


# Common base images and their recommended alternatives
# Organized by base image family
IMAGE_ALTERNATIVES: dict[str, list[ImageAlternative]] = {
    # Python images
    "python": [
        ImageAlternative(
            image="{name}:{version}-slim",
            reason="smaller",
            description="Debian slim variant, ~100MB smaller",
            size_estimate="~150MB",
        ),
        ImageAlternative(
            image="{name}:{version}-alpine",
            reason="alpine",
            description="Alpine Linux base, minimal footprint",
            size_estimate="~50MB",
        ),
        ImageAlternative(
            image="cgr.dev/chainguard/python:latest",
            reason="hardened",
            description="Chainguard hardened image, zero CVEs, distroless",
            size_estimate="~50MB",
        ),
    ],
    
    # Node.js images
    "node": [
        ImageAlternative(
            image="{name}:{version}-slim",
            reason="smaller",
            description="Debian slim variant",
            size_estimate="~200MB",
        ),
        ImageAlternative(
            image="{name}:{version}-alpine",
            reason="alpine",
            description="Alpine Linux base, minimal footprint",
            size_estimate="~130MB",
        ),
        ImageAlternative(
            image="cgr.dev/chainguard/node:latest",
            reason="hardened",
            description="Chainguard hardened image, zero CVEs",
            size_estimate="~100MB",
        ),
    ],
    
    # Golang images
    "golang": [
        ImageAlternative(
            image="{name}:{version}-alpine",
            reason="alpine",
            description="Alpine variant for building",
            size_estimate="~250MB",
        ),
        ImageAlternative(
            image="gcr.io/distroless/static-debian12",
            reason="distroless",
            description="For final stage - static Go binaries only",
            size_estimate="~2MB",
        ),
        ImageAlternative(
            image="cgr.dev/chainguard/go:latest",
            reason="hardened",
            description="Chainguard hardened Go build image",
            size_estimate="~200MB",
        ),
    ],
    
    # Java images
    "openjdk": [
        ImageAlternative(
            image="eclipse-temurin:{version}-jre-alpine",
            reason="alpine",
            description="Eclipse Temurin JRE on Alpine",
            size_estimate="~150MB",
        ),
        ImageAlternative(
            image="gcr.io/distroless/java17-debian12",
            reason="distroless",
            description="Google distroless Java runtime",
            size_estimate="~200MB",
        ),
        ImageAlternative(
            image="cgr.dev/chainguard/jre:latest",
            reason="hardened",
            description="Chainguard hardened JRE",
            size_estimate="~100MB",
        ),
    ],
    
    # Ubuntu/Debian images
    "ubuntu": [
        ImageAlternative(
            image="ubuntu:{version}-minimal",
            reason="smaller",
            description="Ubuntu minimal variant",
            size_estimate="~30MB",
        ),
        ImageAlternative(
            image="debian:{version}-slim",
            reason="smaller",
            description="Debian slim variant",
            size_estimate="~25MB",
        ),
        ImageAlternative(
            image="cgr.dev/chainguard/wolfi-base",
            reason="hardened",
            description="Chainguard Wolfi base, security-focused",
            size_estimate="~15MB",
        ),
    ],
    
    "debian": [
        ImageAlternative(
            image="debian:{version}-slim",
            reason="smaller",
            description="Debian slim variant",
            size_estimate="~25MB",
        ),
        ImageAlternative(
            image="cgr.dev/chainguard/wolfi-base",
            reason="hardened",
            description="Chainguard Wolfi base, security-focused",
            size_estimate="~15MB",
        ),
    ],
    
    # Nginx
    "nginx": [
        ImageAlternative(
            image="nginx:{version}-alpine",
            reason="alpine",
            description="Alpine variant",
            size_estimate="~25MB",
        ),
        ImageAlternative(
            image="cgr.dev/chainguard/nginx:latest",
            reason="hardened",
            description="Chainguard hardened nginx",
            size_estimate="~15MB",
        ),
    ],
    
    # Redis
    "redis": [
        ImageAlternative(
            image="redis:{version}-alpine",
            reason="alpine",
            description="Alpine variant",
            size_estimate="~30MB",
        ),
    ],
    
    # PostgreSQL
    "postgres": [
        ImageAlternative(
            image="postgres:{version}-alpine",
            reason="alpine",
            description="Alpine variant",
            size_estimate="~80MB",
        ),
    ],
}

# Images that are already optimized/hardened
ALREADY_OPTIMIZED = {
    "alpine",
    "distroless",
    "chainguard",
    "wolfi",
    "scratch",
    "busybox",
    "gcr.io/distroless",
    "cgr.dev/chainguard",
}

# Tags that indicate security risk
RISKY_TAGS = {
    "latest",
    "dev",
    "development",
    "beta",
    "rc",
    "nightly",
    "unstable",
}


def get_base_image_name(image: str) -> str:
    """Extract the base image name without registry, tag, or variant."""
    # Drop digest if present
    image = image.split("@", 1)[0]
    # Isolate last path segment (handles registries with ports)
    last_segment = image.rsplit("/", 1)[-1]
    # Remove tag only if it appears after the last "/"
    if ":" in last_segment:
        last_segment = last_segment.rsplit(":", 1)[0]
    return last_segment.lower()


def get_image_tag(image: str) -> str:
    # Drop digest if present
    image = image.split("@", 1)[0]
    last_segment = image.rsplit("/", 1)[-1]
    if ":" in last_segment:
        return last_segment.rsplit(":", 1)[1]
    return "latest"  # Default tag


def is_already_optimized(image: str) -> bool:
    """Check if an image is already considered optimized."""
    image_lower = image.lower()
    
    # Check for optimized registries/prefixes
    for prefix in ALREADY_OPTIMIZED:
        if prefix in image_lower:
            return True
    
    # Check for slim/alpine variants in tag
    tag = get_image_tag(image).lower()
    if any(variant in tag for variant in ["slim", "alpine", "minimal", "distroless"]):
        return True
    
    return False


def has_risky_tag(image: str) -> bool:
    """Check if an image uses a risky tag."""
    tag = get_image_tag(image).lower()
    return tag in RISKY_TAGS


def get_alternatives(image: str) -> list[ImageAlternative]:
    """Get recommended alternatives for a given image."""
    if is_already_optimized(image):
        return []
    
    base_name = get_base_image_name(image)
    tag = get_image_tag(image)
    
    # Extract version from tag (e.g., "3.12-bookworm" -> "3.12")
    version = tag.split("-")[0] if "-" in tag else tag
    
    alternatives = IMAGE_ALTERNATIVES.get(base_name, [])
    
    # Format alternatives with actual version
    result = []
    for alt in alternatives:
        formatted_image = alt.image.format(name=base_name, version=version)
        result.append(ImageAlternative(
            image=formatted_image,
            reason=alt.reason,
            description=alt.description,
            size_estimate=alt.size_estimate,
        ))
    
    return result
