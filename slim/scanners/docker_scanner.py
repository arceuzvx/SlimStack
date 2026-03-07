"""Dockerfile scanner for security and optimization analysis."""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

from slim.core.docker_images import (
    get_alternatives,
    is_already_optimized,
    has_risky_tag,
    get_image_tag,
    ImageAlternative,
)
from slim.core.utils import format_size


@dataclass
class DockerfileIssue:
    """An issue found in a Dockerfile."""
    line_number: int
    severity: str  # "critical", "warning", "info"
    category: str  # "security", "size", "best-practice"
    message: str
    suggestion: str
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        return {
            "line_number": self.line_number,
            "severity": self.severity,
            "category": self.category,
            "message": self.message,
            "suggestion": self.suggestion,
        }


@dataclass
class ImageRecommendation:
    """A recommended alternative for a base image."""
    current_image: str
    recommended_image: str
    reason: str
    description: str
    line_number: int
    size_estimate: str | None = None
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        return {
            "current_image": self.current_image,
            "recommended_image": self.recommended_image,
            "reason": self.reason,
            "description": self.description,
            "line_number": self.line_number,
            "size_estimate": self.size_estimate,
        }


@dataclass
class DockerScanResult:
    """Result of scanning a Dockerfile."""
    dockerfile_path: Path
    base_images: list[tuple[int, str]] = field(default_factory=list)  # (line_num, image)
    issues: list[DockerfileIssue] = field(default_factory=list)
    recommendations: list[ImageRecommendation] = field(default_factory=list)
    multi_stage: bool = False
    stage_count: int = 0
    has_user_instruction: bool = False
    has_healthcheck: bool = False
    total_lines: int = 0
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        return {
            "dockerfile_path": str(self.dockerfile_path),
            "base_images": [
                {"line": line, "image": img} for line, img in self.base_images
            ],
            "issues": [issue.to_dict() for issue in self.issues],
            "recommendations": [rec.to_dict() for rec in self.recommendations],
            "multi_stage": self.multi_stage,
            "stage_count": self.stage_count,
            "has_user_instruction": self.has_user_instruction,
            "has_healthcheck": self.has_healthcheck,
            "total_lines": self.total_lines,
            "summary": {
                "total_issues": len(self.issues),
                "critical": sum(1 for i in self.issues if i.severity == "critical"),
                "warning": sum(1 for i in self.issues if i.severity == "warning"),
                "info": sum(1 for i in self.issues if i.severity == "info"),
                "recommendations_count": len(self.recommendations),
            },
        }


# Patterns for detecting issues
PATTERNS = {
    # FROM instruction - captures image name with optional AS alias
    "from": re.compile(r"^\s*FROM\s+(\S+)(?:\s+AS\s+\S+)?", re.IGNORECASE),
    
    # USER instruction
    "user": re.compile(r"^\s*USER\s+", re.IGNORECASE),
    
    # HEALTHCHECK instruction
    "healthcheck": re.compile(r"^\s*HEALTHCHECK\s+", re.IGNORECASE),
    
    # ADD instruction (potential issue if used for local files)
    "add": re.compile(r"^\s*ADD\s+(?!https?://|--from=)(\S+)", re.IGNORECASE),
    
    # ENV with potential secrets
    "env_secret": re.compile(
        r"^\s*ENV\s+\S*(PASSWORD|SECRET|KEY|TOKEN|CREDENTIAL|API_KEY)\s*=",
        re.IGNORECASE
    ),
    
    # ARG with potential secrets
    "arg_secret": re.compile(
        r"^\s*ARG\s+\S*(PASSWORD|SECRET|KEY|TOKEN|CREDENTIAL|API_KEY)",
        re.IGNORECASE
    ),
    
    # RUN with curl/wget piped to shell (risky)
    "run_pipe_shell": re.compile(
        r"^\s*RUN\s+.*(?:curl|wget)\s+.*\|\s*(?:bash|sh)",
        re.IGNORECASE
    ),
    
    # RUN apt-get without cleanup
    "apt_no_cleanup": re.compile(
        r"^\s*RUN\s+.*apt-get\s+install(?!.*rm\s+-rf\s+/var/lib/apt/lists)",
        re.IGNORECASE
    ),
    
    # RUN npm install without cache clean
    "npm_no_cleanup": re.compile(
        r"^\s*RUN\s+.*npm\s+install(?!.*npm\s+cache\s+clean)",
        re.IGNORECASE
    ),
    
    # RUN pip install without cache optimization
    "pip_no_cache": re.compile(
        r"^\s*RUN\s+.*pip\s+install(?!.*--no-cache-dir)",
        re.IGNORECASE
    ),
    
    # EXPOSE for common sensitive ports
    "expose_sensitive": re.compile(
        r"^\s*EXPOSE\s+(22|23|3389|5432|3306|27017|6379)\b",
        re.IGNORECASE
    ),
    
    # COPY . . at root level (copies everything including .git, secrets)
    "copy_all": re.compile(r"^\s*COPY\s+\.\s+\.", re.IGNORECASE),
}


def find_dockerfile(project_path: Path | None = None) -> Path | None:
    """Find Dockerfile in the project."""
    if project_path is None:
        project_path = Path.cwd()
    
    # Look for Dockerfile (case-insensitive on Windows, case-sensitive on Unix)
    dockerfile_names = ["Dockerfile", "dockerfile", "Dockerfile.prod", "Dockerfile.dev"]
    
    for name in dockerfile_names:
        dockerfile = project_path / name
        if dockerfile.exists():
            return dockerfile
    
    return None


def parse_dockerfile(dockerfile_path: Path) -> list[tuple[int, str]]:
    """Parse a Dockerfile and return list of (line_number, line_content)."""
    lines = []
    try:
        content = dockerfile_path.read_text(encoding="utf-8")
        for i, line in enumerate(content.splitlines(), start=1):
            lines.append((i, line))
    except OSError as e:
        # Log or handle file access errors appropriately
        import logging
        logging.warning(f"Failed to read Dockerfile {dockerfile_path}: {e}")
    return lines


def analyze_dockerfile(lines: list[tuple[int, str]], has_dockerignore: bool = False) -> DockerScanResult:
    """Analyze Dockerfile lines for issues and recommendations."""
    result = DockerScanResult(
        dockerfile_path=Path("Dockerfile"),
        total_lines=len(lines),
    )
    
    # Track state
    from_images: list[tuple[int, str]] = []
    has_user = False
    has_healthcheck = False
    last_from_line = 0
    
    for line_num, line in lines:
        # Skip comments and empty lines
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        
        # Check FROM instruction
        from_match = PATTERNS["from"].match(stripped)
        if from_match:
            image = from_match.group(1)
            from_images.append((line_num, image))
            last_from_line = line_num
            
            # Check for risky tag
            if has_risky_tag(image):
                result.issues.append(DockerfileIssue(
                    line_number=line_num,
                    severity="warning",
                    category="security",
                    message=f"Image uses unpinned '{get_image_tag(image)}' tag",
                    suggestion="Pin to a specific version tag for reproducible builds",
                ))
            
            # Get alternatives if not already optimized
            if not is_already_optimized(image):
                alternatives = get_alternatives(image)
                for alt in alternatives[:2]:  # Top 2 recommendations
                    result.recommendations.append(ImageRecommendation(
                        current_image=image,
                        recommended_image=alt.image,
                        reason=alt.reason,
                        description=alt.description,
                        line_number=line_num,
                        size_estimate=alt.size_estimate,
                    ))
        
        # Check USER instruction
        if PATTERNS["user"].match(stripped):
            has_user = True
        
        # Check HEALTHCHECK instruction
        if PATTERNS["healthcheck"].match(stripped):
            has_healthcheck = True
        
        # Check ADD for local files (should use COPY)
        add_match = PATTERNS["add"].match(stripped)
        if add_match:
            result.issues.append(DockerfileIssue(
                line_number=line_num,
                severity="info",
                category="best-practice",
                message="Using ADD for local files",
                suggestion="Use COPY instead of ADD for local files (ADD has extra features that may be unexpected)",
            ))
        
        # Check for secrets in ENV
        if PATTERNS["env_secret"].match(stripped):
            result.issues.append(DockerfileIssue(
                line_number=line_num,
                severity="critical",
                category="security",
                message="Potential secret exposed in ENV instruction",
                suggestion="Use Docker secrets or mount secrets at runtime instead of ENV",
            ))
        
        # Check for secrets in ARG
        if PATTERNS["arg_secret"].match(stripped):
            result.issues.append(DockerfileIssue(
                line_number=line_num,
                severity="warning",
                category="security",
                message="Potential secret in ARG instruction",
                suggestion="ARG values are visible in image history. Use build secrets (--secret) instead",
            ))
        
        # Check for curl/wget piped to shell
        if PATTERNS["run_pipe_shell"].match(stripped):
            result.issues.append(DockerfileIssue(
                line_number=line_num,
                severity="warning",
                category="security",
                message="Piping remote script to shell",
                suggestion="Download and verify scripts before executing, or use package managers",
            ))
        
        # Check for apt-get without cleanup
        if PATTERNS["apt_no_cleanup"].match(stripped):
            result.issues.append(DockerfileIssue(
                line_number=line_num,
                severity="info",
                category="size",
                message="apt-get install without cleanup",
                suggestion="Add 'rm -rf /var/lib/apt/lists/*' to reduce image size",
            ))
        
        # Check for pip without --no-cache-dir
        if PATTERNS["pip_no_cache"].match(stripped):
            result.issues.append(DockerfileIssue(
                line_number=line_num,
                severity="info",
                category="size",
                message="pip install without cache optimization",
                suggestion="Add '--no-cache-dir' to pip install to reduce image size",
            ))
        
        # Check COPY . . (copies everything)
        if PATTERNS["copy_all"].match(stripped):
            if has_dockerignore:
                result.issues.append(DockerfileIssue(
                    line_number=line_num,
                    severity="info",
                    category="best-practice",
                    message="COPY . . used (mitigated by .dockerignore)",
                    suggestion="Verify .dockerignore excludes .git, .env, secrets, and node_modules",
                ))
            else:
                result.issues.append(DockerfileIssue(
                    line_number=line_num,
                    severity="warning",
                    category="security",
                    message="COPY . . may include sensitive files (.git, .env, secrets)",
                    suggestion="Add a .dockerignore file or copy specific files/directories",
                ))
    
    # Set result properties
    result.base_images = from_images
    result.stage_count = len(from_images)
    result.multi_stage = len(from_images) > 1
    result.has_user_instruction = has_user
    result.has_healthcheck = has_healthcheck
    
    # Add issue if running as root (no USER instruction)
    if not has_user and from_images:
        result.issues.append(DockerfileIssue(
            line_number=last_from_line,
            severity="warning",
            category="security",
            message="Container runs as root (no USER instruction)",
            suggestion="Add 'USER nonroot' or 'USER 1000' to run as non-root user",
        ))
    
    # Add info if no HEALTHCHECK
    if not has_healthcheck and from_images:
        result.issues.append(DockerfileIssue(
            line_number=last_from_line,
            severity="info",
            category="best-practice",
            message="No HEALTHCHECK instruction",
            suggestion="Add HEALTHCHECK for container orchestration and health monitoring",
        ))
    
    # Suggest multi-stage build for non-multi-stage Dockerfiles with build tools
    if not result.multi_stage and from_images:
        base_image = from_images[0][1].lower()
        if any(lang in base_image for lang in ["golang", "rust", "node", "python", "java", "maven", "gradle"]):
            result.issues.append(DockerfileIssue(
                line_number=from_images[0][0],
                severity="info",
                category="size",
                message="Consider using multi-stage build",
                suggestion="Multi-stage builds can significantly reduce final image size by excluding build tools",
            ))
    
    # Sort issues by severity
    severity_order = {"critical": 0, "warning": 1, "info": 2}
    result.issues.sort(key=lambda x: severity_order.get(x.severity, 3))
    
    return result


def scan_dockerfile(
    project_path: Path | None = None,
    dockerfile_path: Path | None = None,
) -> DockerScanResult:
    """
    Scan a Dockerfile for security issues and optimization opportunities.
    
    Args:
        project_path: Path to the project directory (looks for Dockerfile)
        dockerfile_path: Direct path to a Dockerfile (overrides project_path)
    
    Returns:
        DockerScanResult with issues and recommendations
    """
    # Find the Dockerfile
    if dockerfile_path is None:
        dockerfile_path = find_dockerfile(project_path)
    
    if dockerfile_path is None or not dockerfile_path.exists():
        # Return empty result with path set
        result = DockerScanResult(
            dockerfile_path=Path(project_path or Path.cwd()) / "Dockerfile"
        )
        result.issues.append(DockerfileIssue(
            line_number=0,
            severity="critical",
            category="best-practice",
            message="No Dockerfile found",
            suggestion="Create a Dockerfile in the project root",
        ))
        return result
    
    # Parse and analyze
    lines = parse_dockerfile(dockerfile_path)
    
    # Check for .dockerignore
    dockerignore_path = dockerfile_path.parent / ".dockerignore"
    has_dockerignore = dockerignore_path.is_file()
    
    result = analyze_dockerfile(lines, has_dockerignore=has_dockerignore)
    result.dockerfile_path = dockerfile_path
    
    return result


def get_scan_result_dict(result: DockerScanResult) -> dict:
    """Convert scan result to JSON-serializable dictionary."""
    return result.to_dict()
