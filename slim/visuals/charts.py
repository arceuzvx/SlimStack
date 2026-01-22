"""ASCII bar chart rendering for CLI output."""

from slim.core.config import Colors
from slim.core.utils import is_tty, format_size


def render_bar_chart(
    items: list[tuple[str, int]],
    title: str = "",
    max_bar_width: int = 40,
    show_size: bool = True,
    filled_char: str = "█",
    empty_char: str = "░",
) -> str:
    """
    Render a horizontal ASCII bar chart.
    
    Args:
        items: List of (label, value) tuples
        title: Chart title
        max_bar_width: Maximum width of the bar portion
        show_size: Whether to show size values
        filled_char: Character for filled portion
        empty_char: Character for empty portion
    
    Returns:
        Formatted chart string
    """
    colors_enabled = is_tty()
    lines = []
    
    if not items:
        return "  (no data)"
    
    # Title
    if title:
        if colors_enabled:
            lines.append(f"\n{Colors.BOLD}{title}{Colors.RESET}")
        else:
            lines.append(f"\n{title}")
        lines.append("─" * len(title))
    
    # Find max value for scaling
    max_value = max(v for _, v in items) if items else 1
    if max_value == 0:
        max_value = 1
    
    # Find max label width
    max_label_width = max(len(label) for label, _ in items) if items else 0
    
    # Colors for bars
    bar_colors = [Colors.CYAN, Colors.GREEN, Colors.YELLOW, Colors.MAGENTA, Colors.BLUE]
    
    for i, (label, value) in enumerate(items):
        # Calculate bar width
        bar_width = int((value / max_value) * max_bar_width)
        bar_width = max(bar_width, 0)  # Ensure non-negative
        
        # Build bar
        filled = filled_char * bar_width
        empty = empty_char * (max_bar_width - bar_width)
        
        if colors_enabled:
            color = bar_colors[i % len(bar_colors)]
            bar = f"{color}{filled}{Colors.DIM}{empty}{Colors.RESET}"
        else:
            bar = filled + empty
        
        # Format label
        label_padded = label.ljust(max_label_width)
        
        # Format size
        if show_size:
            size_str = format_size(value)
            line = f"  {label_padded}  {bar}  {size_str}"
        else:
            line = f"  {label_padded}  {bar}"
        
        lines.append(line)
    
    return "\n".join(lines)


def render_disk_chart(
    python_size: int,
    node_size: int,
    docker_size: int,
    title: str = "Disk Usage by Ecosystem",
) -> str:
    """
    Render a disk usage chart for all ecosystems.
    
    Args:
        python_size: Python ecosystem size in bytes
        node_size: Node.js ecosystem size in bytes
        docker_size: Docker ecosystem size in bytes
        title: Chart title
    
    Returns:
        Formatted chart string
    """
    items = [
        ("Python", python_size),
        ("Node.js", node_size),
        ("Docker", docker_size),
    ]
    
    # Filter out zero values
    items = [(label, size) for label, size in items if size > 0]
    
    if not items:
        return "  No ecosystem data found."
    
    return render_bar_chart(items, title=title)


def render_project_chart(
    projects: list[tuple[str, str, int]],
    title: str = "Projects by Size",
    top_n: int = 10,
) -> str:
    """
    Render a chart of projects by size.
    
    Args:
        projects: List of (name, ecosystem, size_bytes) tuples
        title: Chart title
        top_n: Maximum number of projects to show
    
    Returns:
        Formatted chart string
    """
    colors_enabled = is_tty()
    
    # Sort by size and take top N
    sorted_projects = sorted(projects, key=lambda x: x[2], reverse=True)[:top_n]
    
    if not sorted_projects:
        return "  No projects found."
    
    # Convert to items for bar chart
    items = [
        (f"{name} ({ecosystem[:2]})", size)
        for name, ecosystem, size in sorted_projects
    ]
    
    return render_bar_chart(items, title=title)


def render_percentage_bar(
    used: int,
    total: int,
    width: int = 30,
    label: str = "",
) -> str:
    """
    Render a single percentage bar.
    
    Args:
        used: Amount used
        total: Total amount
        width: Bar width in characters
        label: Optional label prefix
    
    Returns:
        Formatted bar string
    """
    colors_enabled = is_tty()
    
    if total == 0:
        percentage = 0
    else:
        percentage = (used / total) * 100
    
    filled = int((percentage / 100) * width)
    empty = width - filled
    
    if colors_enabled:
        if percentage < 50:
            color = Colors.GREEN
        elif percentage < 80:
            color = Colors.YELLOW
        else:
            color = Colors.RED
        
        bar = f"{color}{'█' * filled}{Colors.DIM}{'░' * empty}{Colors.RESET}"
    else:
        bar = "█" * filled + "░" * empty
    
    result = f"[{bar}] {percentage:5.1f}%"
    
    if label:
        result = f"{label}: {result}"
    
    return result
