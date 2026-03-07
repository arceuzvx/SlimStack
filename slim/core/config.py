"""Configuration constants for SlimStack."""

from typing import Final

# Version info
VERSION: Final[str] = "0.2.0"

# Protected packages - never uninstall these
PYTHON_PROTECTED_PACKAGES: Final[frozenset[str]] = frozenset({
    "pip",
    "setuptools",
    "wheel",
    "pkg_resources",
    "distribute",
})

# Standard library modules - not installable packages
# This is a subset, we'll detect more via sys.stdlib_module_names
PYTHON_STDLIB_PREFIXES: Final[frozenset[str]] = frozenset({
    "os", "sys", "re", "json", "ast", "typing", "pathlib", "subprocess",
    "collections", "itertools", "functools", "operator", "string",
    "datetime", "time", "calendar", "math", "random", "statistics",
    "io", "struct", "codecs", "unicodedata", "textwrap",
    "copy", "pprint", "enum", "graphlib", "types",
    "abc", "contextlib", "dataclasses",
    "argparse", "logging", "warnings", "traceback",
    "unittest", "doctest",
    "threading", "multiprocessing", "concurrent", "asyncio",
    "socket", "ssl", "email", "html", "xml", "urllib",
    "http", "ftplib", "smtplib", "imaplib",
    "hashlib", "hmac", "secrets",
    "sqlite3", "dbm", "shelve", "pickle", "marshal",
    "zipfile", "tarfile", "gzip", "bz2", "lzma", "zlib",
    "csv", "configparser", "tomllib",
    "shutil", "glob", "fnmatch", "tempfile", "fileinput",
    "platform", "ctypes", "sysconfig",
    "_thread", "__future__", "builtins",
})

# Node.js built-in modules
NODE_BUILTIN_MODULES: Final[frozenset[str]] = frozenset({
    "assert", "buffer", "child_process", "cluster", "console",
    "constants", "crypto", "dgram", "dns", "domain", "events",
    "fs", "http", "http2", "https", "inspector", "module", "net",
    "os", "path", "perf_hooks", "process", "punycode", "querystring",
    "readline", "repl", "stream", "string_decoder", "sys", "timers",
    "tls", "trace_events", "tty", "url", "util", "v8", "vm", "wasi",
    "worker_threads", "zlib",
    # Node.js prefixed modules
    "node:assert", "node:buffer", "node:child_process", "node:cluster",
    "node:console", "node:constants", "node:crypto", "node:dgram",
    "node:dns", "node:domain", "node:events", "node:fs", "node:http",
    "node:http2", "node:https", "node:inspector", "node:module",
    "node:net", "node:os", "node:path", "node:perf_hooks", "node:process",
    "node:punycode", "node:querystring", "node:readline", "node:repl",
    "node:stream", "node:string_decoder", "node:sys", "node:timers",
    "node:tls", "node:trace_events", "node:tty", "node:url", "node:util",
    "node:v8", "node:vm", "node:wasi", "node:worker_threads", "node:zlib",
})

# File extensions to scan
PYTHON_EXTENSIONS: Final[tuple[str, ...]] = (".py", ".pyw")
JS_EXTENSIONS: Final[tuple[str, ...]] = (".js", ".jsx", ".mjs", ".cjs")
TS_EXTENSIONS: Final[tuple[str, ...]] = (".ts", ".tsx", ".mts", ".cts")
NODE_EXTENSIONS: Final[tuple[str, ...]] = JS_EXTENSIONS + TS_EXTENSIONS

# Directories to skip during scanning
SKIP_DIRECTORIES: Final[frozenset[str]] = frozenset({
    "__pycache__",
    ".git",
    ".svn",
    ".hg",
    "node_modules",
    "venv",
    ".venv",
    "env",
    ".env",
    ".tox",
    ".nox",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    "egg-info",
    ".eggs",
    "site-packages",
})

# ANSI color codes for terminal output
class Colors:
    """ANSI color codes for terminal output."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    
    @classmethod
    def disable(cls) -> None:
        """Disable all colors (for non-TTY output)."""
        cls.RESET = ""
        cls.BOLD = ""
        cls.DIM = ""
        cls.RED = ""
        cls.GREEN = ""
        cls.YELLOW = ""
        cls.BLUE = ""
        cls.MAGENTA = ""
        cls.CYAN = ""
        cls.WHITE = ""
        cls.BG_RED = ""
        cls.BG_GREEN = ""
        cls.BG_YELLOW = ""
