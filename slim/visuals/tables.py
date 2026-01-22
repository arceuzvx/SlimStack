"""ASCII table rendering for CLI output."""

from typing import Any
from slim.core.config import Colors
from slim.core.utils import is_tty


def render_table(
    headers: list[str],
    rows: list[list[Any]],
    alignments: list[str] | None = None,
    max_width: int = 80,
) -> str:
    """
    Render a simple ASCII table.
    
    Args:
        headers: Column headers
        rows: List of rows, each row is a list of values
        alignments: List of "l", "r", or "c" for each column
        max_width: Maximum table width
    
    Returns:
        Formatted table string
    """
    if not headers:
        return ""
    
    num_cols = len(headers)
    
    if alignments is None:
        alignments = ["l"] * num_cols
    
    # Convert all values to strings
    str_headers = [str(h) for h in headers]
    str_rows = [[str(v) for v in row] for row in rows]
    
    # Calculate column widths
    col_widths = [len(h) for h in str_headers]
    for row in str_rows:
        for i, val in enumerate(row):
            if i < num_cols:
                col_widths[i] = max(col_widths[i], len(val))
    
    # Ensure minimum width
    col_widths = [max(w, 3) for w in col_widths]
    
    # Build format strings
    def format_cell(value: str, width: int, align: str) -> str:
        if align == "r":
            return value.rjust(width)
        elif align == "c":
            return value.center(width)
        return value.ljust(width)
    
    lines = []
    
    # Header
    header_cells = [
        format_cell(h, col_widths[i], alignments[i])
        for i, h in enumerate(str_headers)
    ]
    lines.append(" │ ".join(header_cells))
    
    # Separator
    sep_cells = ["─" * w for w in col_widths]
    lines.append("─┼─".join(sep_cells))
    
    # Rows
    for row in str_rows:
        # Pad row if needed
        while len(row) < num_cols:
            row.append("")
        
        row_cells = [
            format_cell(row[i], col_widths[i], alignments[i])
            for i in range(num_cols)
        ]
        lines.append(" │ ".join(row_cells))
    
    return "\n".join(lines)


def render_package_table(
    packages: list[tuple[str, str, str]],
    title: str = "Packages",
) -> str:
    """
    Render a table of packages with status and size.
    
    Args:
        packages: List of (name, status, size) tuples
        title: Table title
    
    Returns:
        Formatted table string
    """
    colors_enabled = is_tty()
    
    lines = []
    
    # Title
    if title:
        if colors_enabled:
            lines.append(f"\n{Colors.BOLD}{title}{Colors.RESET}")
        else:
            lines.append(f"\n{title}")
        lines.append("=" * len(title))
    
    if not packages:
        lines.append("  (none)")
        return "\n".join(lines)
    
    # Color-code status
    def color_status(status: str) -> str:
        if not colors_enabled:
            return status
        
        status_lower = status.lower()
        if status_lower in ("used", "ok"):
            return f"{Colors.GREEN}{status}{Colors.RESET}"
        elif status_lower in ("unused", "removable"):
            return f"{Colors.YELLOW}{status}{Colors.RESET}"
        elif status_lower in ("unknown", "error"):
            return f"{Colors.RED}{status}{Colors.RESET}"
        return status
    
    # Build table
    headers = ["Package", "Status", "Size"]
    rows = [
        [name, color_status(status), size]
        for name, status, size in packages
    ]
    
    table = render_table(headers, rows, alignments=["l", "c", "r"])
    lines.append(table)
    
    return "\n".join(lines)


def render_summary_box(
    title: str,
    items: list[tuple[str, str]],
) -> str:
    """
    Render a summary box with key-value pairs.
    
    Args:
        title: Box title
        items: List of (key, value) tuples
    
    Returns:
        Formatted box string
    """
    colors_enabled = is_tty()
    lines = []
    
    # Calculate widths
    key_width = max(len(k) for k, _ in items) if items else 0
    val_width = max(len(v) for _, v in items) if items else 0
    
    inner_width = key_width + val_width + 3  # " : " separator
    box_width = max(inner_width + 4, len(title) + 4)  # padding
    
    # Top border
    lines.append("┌" + "─" * (box_width - 2) + "┐")
    
    # Title
    title_padded = title.center(box_width - 4)
    if colors_enabled:
        lines.append(f"│ {Colors.BOLD}{title_padded}{Colors.RESET} │")
    else:
        lines.append(f"│ {title_padded} │")
    
    # Separator
    lines.append("├" + "─" * (box_width - 2) + "┤")
    
    # Items
    for key, value in items:
        key_padded = key.ljust(key_width)
        val_padded = value.rjust(val_width)
        content = f"{key_padded} : {val_padded}"
        content_padded = content.ljust(box_width - 4)
        lines.append(f"│ {content_padded} │")
    
    # Bottom border
    lines.append("└" + "─" * (box_width - 2) + "┘")
    
    return "\n".join(lines)
