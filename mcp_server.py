"""
Cascade — MCP Tool Server (mcp_server.py)
==========================================
Implements an MCP server using FastMCP that gives the Cascade agent
"hands and eyes" to inspect, read, and organize the local filesystem.

Tools exposed:
  • list_files(directory)                  — Observe the environment
  • read_file(filename, directory)         — Analyze file contents
  • move_file(filename, source_dir, category) — Execute reorganization
  • get_file_metadata(filename, directory) — Retrieve file stats
  • search_content(directory, keyword)     — Full-text search across files
  • extract_schema(directory)              — Produce structured JSON inventory schema

Transports:
  stdio (default) — python mcp_server.py
  SSE             — python mcp_server.py --sse [--host 0.0.0.0] [--port 8000]
"""

import os
import sys
import json
import csv
import shutil
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional

from mcp.server.fastmcp import FastMCP


# ─── Server Initialization ────────────────────────────────────────────────────

mcp = FastMCP(
    name="Cascade",
    version="1.0.0",
    description=(
        "Cascade agentic file organization server. Provides tools to list, read, "
        "move, search, and extract structured schemas from unstructured data silos — "
        "enabling LLM agents to autonomously convert multi-format enterprise data "
        "into structured, analytics-ready information."
    ),
)


# ─── Utility Helpers ──────────────────────────────────────────────────────────

READABLE_EXTENSIONS = {
    ".txt", ".py", ".js", ".ts", ".html", ".css", ".json",
    ".csv", ".md", ".yaml", ".yml", ".toml", ".ini", ".cfg",
    ".xml", ".sh", ".bat", ".env", ".log", ".sql", ".r",
    ".java", ".cpp", ".c", ".h", ".go", ".rs", ".rb",
}

BINARY_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp",
    ".mp3", ".wav", ".ogg", ".flac", ".aac",
    ".mp4", ".avi", ".mov", ".mkv",
    ".zip", ".tar", ".gz", ".rar", ".7z",
    ".exe", ".dll", ".so", ".pdf", ".docx", ".doc",
}

CATEGORY_MAP = {
    "Media":    {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp",
                 ".mp3", ".wav", ".ogg", ".flac", ".aac",
                 ".mp4", ".avi", ".mov", ".mkv"},
    "Code":     {".py", ".js", ".ts", ".java", ".cpp", ".c", ".h",
                 ".go", ".rs", ".rb", ".sh", ".bat", ".html", ".css"},
    "Data":     {".csv", ".json", ".xml", ".yaml", ".yml", ".sql",
                 ".toml", ".parquet", ".feather"},
    "Finance":  set(),   # identified by content keywords
    "Docs":     {".txt", ".md", ".pdf", ".docx", ".doc", ".odt",
                 ".rtf", ".log"},
    "Archives": {".zip", ".tar", ".gz", ".rar", ".7z"},
    "Config":   {".ini", ".cfg", ".env", ".toml", ".yaml", ".yml"},
}

FINANCE_KEYWORDS = {
    "swift", "iban", "ifsc", "routing", "account", "bank",
    "finance", "treasury", "invoice", "transaction", "salary",
    "ledger", "payroll", "tax", "revenue", "credit", "debit",
}


def _resolve_path(directory: str) -> Path:
    """Resolve and validate a directory path."""
    p = Path(directory).expanduser().resolve()
    if not p.exists():
        raise FileNotFoundError(f"Directory not found: {p}")
    if not p.is_dir():
        raise NotADirectoryError(f"Not a directory: {p}")
    return p


def _safe_read_text(filepath: Path, max_bytes: int = 32_768) -> str:
    """Read text content from a file, handling binary and encoding issues."""
    ext = filepath.suffix.lower()

    if ext in BINARY_EXTENSIONS:
        return (
            f"[BINARY FILE — {ext.upper()[1:]} format]\n"
            f"Size: {filepath.stat().st_size} bytes\n"
            f"Cannot extract text directly. Use a specialized parser."
        )

    if ext == ".csv":
        try:
            with open(filepath, newline="", encoding="utf-8", errors="replace") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            header = list(rows[0].keys()) if rows else []
            preview = rows[:10]
            return (
                f"[CSV FILE — {len(rows)} rows × {len(header)} columns]\n"
                f"Columns: {', '.join(header)}\n\n"
                f"First 10 rows:\n"
                + "\n".join(json.dumps(r) for r in preview)
            )
        except Exception:
            pass  # fall through to plain read

    try:
        raw = filepath.read_bytes()[:max_bytes]
        return raw.decode("utf-8", errors="replace")
    except Exception as e:
        return f"[ERROR reading file: {e}]"


def _guess_category(filepath: Path, content: Optional[str] = None) -> str:
    """Heuristically determine the best category for a file."""
    ext = filepath.suffix.lower()

    for category, exts in CATEGORY_MAP.items():
        if ext in exts:
            # For ambiguous doc-type text files, check content too
            if category == "Docs" and content:
                lower = content.lower()
                if any(kw in lower for kw in FINANCE_KEYWORDS):
                    return "Finance"
            return category

    # Content-based fallback
    if content:
        lower = content.lower()
        if any(kw in lower for kw in FINANCE_KEYWORDS):
            return "Finance"
        if any(kw in lower for kw in {"def ", "class ", "import ", "function", "var ", "const "}):
            return "Code"

    return "Misc"


def _has_finance_signals(content: str) -> bool:
    """Check if file content contains finance-related signals."""
    lower = content.lower()
    return any(kw in lower for kw in FINANCE_KEYWORDS)


# ─── MCP Tools ────────────────────────────────────────────────────────────────

@mcp.tool()
def list_files(directory: str) -> str:
    """
    List all files in a given directory (non-recursive, top-level only).
    Returns filenames with their sizes, suggested categories, and readability.

    Args:
        directory: Absolute or relative path to the directory to scan.

    Returns:
        Formatted string listing all files with metadata.
    """
    try:
        dir_path = _resolve_path(directory)
    except (FileNotFoundError, NotADirectoryError) as e:
        return f"ERROR: {e}"

    files = [f for f in dir_path.iterdir() if f.is_file()]
    dirs  = [d for d in dir_path.iterdir() if d.is_dir()]

    if not files and not dirs:
        return f"Directory '{dir_path}' is empty."

    lines = [
        f"📁 Directory: {dir_path}",
        f"   Files: {len(files)}  |  Subdirectories: {len(dirs)}",
        "─" * 54,
    ]

    for f in sorted(files):
        stat = f.stat()
        size_kb = stat.st_size / 1024
        ext = f.suffix.lower()
        category = _guess_category(f)
        readable = "✓" if ext in READABLE_EXTENSIONS else "✗"
        lines.append(
            f"  📄 {f.name:<32} {size_kb:>6.1f} KB  [{category:<8}]  readable:{readable}"
        )

    if dirs:
        lines.append("─" * 54)
        lines.append("Subdirectories:")
        for d in sorted(dirs):
            count = sum(1 for _ in d.iterdir())
            lines.append(f"  📁 {d.name}/ ({count} items)")

    return "\n".join(lines)


@mcp.tool()
def read_file(filename: str, directory: str) -> str:
    """
    Read and return the text content of a file for analysis.
    Handles CSV (structured preview), plain text, code, and JSON.
    Binary files (images, audio, archives, PDFs) return metadata only.

    Args:
        filename:  Name of the file to read.
        directory: Directory containing the file.

    Returns:
        File contents as a string, or metadata for binary files.
    """
    try:
        dir_path = _resolve_path(directory)
    except (FileNotFoundError, NotADirectoryError) as e:
        return f"ERROR: {e}"

    filepath = dir_path / filename
    if not filepath.exists():
        return f"ERROR: File '{filename}' not found in '{directory}'."
    if not filepath.is_file():
        return f"ERROR: '{filename}' is not a file."

    content = _safe_read_text(filepath)
    category = _guess_category(filepath, content)

    return (
        f"📄 File: {filename}\n"
        f"   Path: {filepath}\n"
        f"   Size: {filepath.stat().st_size} bytes\n"
        f"   Extension: {filepath.suffix}\n"
        f"   Suggested Category: {category}\n"
        f"{'─'*54}\n"
        f"{content}\n"
        f"{'─'*54}"
    )


@mcp.tool()
def move_file(filename: str, source_dir: str, category: str) -> str:
    """
    Move a file into a named category subdirectory within source_dir.
    Automatically creates the subdirectory if it does not exist.
    Handles filename collisions by appending a timestamp.

    Args:
        filename:   Name of the file to move.
        source_dir: Current directory containing the file.
        category:   Target category name (becomes a subdirectory).

    Returns:
        Success or error message with the new file path.
    """
    try:
        src_dir = _resolve_path(source_dir)
    except (FileNotFoundError, NotADirectoryError) as e:
        return f"ERROR: {e}"

    src_file = src_dir / filename
    if not src_file.exists():
        return f"ERROR: File '{filename}' not found in '{source_dir}'."

    safe_category = Path(category).name  # Prevent path traversal
    target_dir  = src_dir / safe_category
    target_file = target_dir / filename

    if target_file.exists():
        stem   = src_file.stem
        suffix = src_file.suffix
        ts     = datetime.now().strftime("%Y%m%d_%H%M%S")
        target_file = target_dir / f"{stem}_{ts}{suffix}"

    target_dir.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src_file), str(target_file))

    return (
        f"✅ Moved: '{filename}'\n"
        f"   From:     {src_file}\n"
        f"   To:       {target_file}\n"
        f"   Category: {safe_category}"
    )


@mcp.tool()
def get_file_metadata(filename: str, directory: str) -> str:
    """
    Retrieve detailed metadata for a file: size, extension, timestamps,
    suggested category, and readability flags.

    Args:
        filename:  File name.
        directory: Directory containing the file.

    Returns:
        JSON-formatted metadata string.
    """
    try:
        dir_path = _resolve_path(directory)
    except (FileNotFoundError, NotADirectoryError) as e:
        return f"ERROR: {e}"

    filepath = dir_path / filename
    if not filepath.exists():
        return f"ERROR: File '{filename}' not found."

    stat = filepath.stat()
    ext  = filepath.suffix.lower()

    meta = {
        "filename":            filename,
        "path":                str(filepath),
        "extension":           ext,
        "size_bytes":          stat.st_size,
        "size_kb":             round(stat.st_size / 1024, 2),
        "is_readable":         ext in READABLE_EXTENSIONS,
        "is_binary":           ext in BINARY_EXTENSIONS,
        "suggested_category":  _guess_category(filepath),
        "created":             datetime.fromtimestamp(stat.st_ctime).isoformat(),
        "modified":            datetime.fromtimestamp(stat.st_mtime).isoformat(),
    }

    return json.dumps(meta, indent=2)


@mcp.tool()
def search_content(directory: str, keyword: str) -> str:
    """
    Search all readable files in a directory tree for a keyword (case-insensitive).
    Returns matching filenames and the specific lines containing the keyword.

    Args:
        directory: Directory to search (searches recursively).
        keyword:   Case-insensitive search term.

    Returns:
        Formatted string of matches, or a no-results message.
    """
    try:
        dir_path = _resolve_path(directory)
    except (FileNotFoundError, NotADirectoryError) as e:
        return f"ERROR: {e}"

    keyword_lower = keyword.lower()
    matches = []

    for filepath in sorted(dir_path.rglob("*")):
        if not filepath.is_file():
            continue
        if filepath.suffix.lower() not in READABLE_EXTENSIONS:
            continue
        try:
            text = filepath.read_text(encoding="utf-8", errors="replace")
            hits = [
                (i + 1, line.strip())
                for i, line in enumerate(text.splitlines())
                if keyword_lower in line.lower()
            ]
            if hits:
                matches.append((filepath.relative_to(dir_path), hits))
        except Exception:
            continue

    if not matches:
        return f"🔍 No matches found for '{keyword}' in '{dir_path}'."

    lines = [f"🔍 Search results for '{keyword}' in '{dir_path}':", "─" * 54]
    for rel_path, hits in matches:
        lines.append(f"\n  📄 {rel_path}:")
        for lineno, line_text in hits[:5]:
            lines.append(f"     Line {lineno:>4}: {line_text[:120]}")

    return "\n".join(lines)


@mcp.tool()
def extract_schema(directory: str) -> str:
    """
    Scan all files in a directory and produce a machine-readable JSON schema
    that represents the structured inventory of the data silo. Each file is
    described with its category, size, readability, content preview, and any
    detected finance signals. This converts raw unstructured file dumps into
    analytics-ready structured metadata.

    Args:
        directory: Directory to scan (non-recursive, top-level files only).

    Returns:
        A JSON string containing the structured schema of the directory.
    """
    try:
        dir_path = _resolve_path(directory)
    except (FileNotFoundError, NotADirectoryError) as e:
        return f"ERROR: {e}"

    schema_records = []
    category_summary: dict[str, list[str]] = {}

    for filepath in sorted(dir_path.rglob("*")):
        if not filepath.is_file():
            continue

        ext       = filepath.suffix.lower()
        stat      = filepath.stat()
        is_readable = ext in READABLE_EXTENSIONS
        content_preview = ""
        finance_signals = False
        extracted_keys: list[str] = []

        if is_readable:
            raw_content = _safe_read_text(filepath, max_bytes=4096)
            content_preview = raw_content[:200].replace("\n", " ").strip()
            finance_signals = _has_finance_signals(raw_content)

            # For JSON files, extract top-level keys
            if ext == ".json":
                try:
                    data = json.loads(filepath.read_text(encoding="utf-8", errors="replace"))
                    if isinstance(data, dict):
                        extracted_keys = list(data.keys())
                except Exception:
                    pass

            # For CSV files, extract column names
            elif ext == ".csv":
                try:
                    with open(filepath, newline="", encoding="utf-8", errors="replace") as f:
                        reader = csv.DictReader(f)
                        if reader.fieldnames:
                            extracted_keys = list(reader.fieldnames)
                except Exception:
                    pass

        category = _guess_category(filepath, content_preview if is_readable else None)

        # Build relative path from directory root
        try:
            rel_path = str(filepath.relative_to(dir_path))
        except ValueError:
            rel_path = filepath.name

        record = {
            "filename":        filepath.name,
            "relative_path":   rel_path,
            "extension":       ext,
            "category":        category,
            "size_bytes":      stat.st_size,
            "size_kb":         round(stat.st_size / 1024, 2),
            "is_readable":     is_readable,
            "is_binary":       ext in BINARY_EXTENSIONS,
            "finance_signals": finance_signals,
            "content_preview": content_preview,
            "extracted_keys":  extracted_keys,
            "modified":        datetime.fromtimestamp(stat.st_mtime).isoformat(),
        }

        schema_records.append(record)
        category_summary.setdefault(category, []).append(filepath.name)

    schema_output = {
        "cascade_schema_version": "1.0",
        "directory":              str(dir_path),
        "generated_at":           datetime.now().isoformat(),
        "total_files":            len(schema_records),
        "category_summary":       {cat: {"count": len(files), "files": files}
                                   for cat, files in sorted(category_summary.items())},
        "files":                  schema_records,
    }

    return json.dumps(schema_output, indent=2)


# ─── Entry Point ──────────────────────────────────────────────────────────────

def _parse_server_args():
    parser = argparse.ArgumentParser(
        prog="mcp_server",
        description="Cascade MCP Tool Server",
    )
    parser.add_argument("--sse", action="store_true",
                        help="Use SSE transport instead of stdio")
    parser.add_argument("--host", default="0.0.0.0",
                        help="SSE host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000,
                        help="SSE port (default: 8000)")
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_server_args()

    if args.sse:
        print(f"🚀 Cascade MCP Server starting (SSE transport)")
        print(f"   Host : {args.host}")
        print(f"   Port : {args.port}")
        print(f"   URL  : http://{args.host}:{args.port}/sse")
        print(f"   Tools: list_files, read_file, move_file,")
        print(f"           get_file_metadata, search_content, extract_schema")
        mcp.run(transport="sse", host=args.host, port=args.port)
    else:
        print("🚀 Cascade MCP Server starting (stdio transport)")
        print("   Tools: list_files, read_file, move_file,")
        print("          get_file_metadata, search_content, extract_schema")
        mcp.run(transport="stdio")
