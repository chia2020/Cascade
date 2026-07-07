"""
Cascade — Test Data Seeder (setup_data.py)
==========================================
Creates a test_dump/ directory populated with diverse sample files
spanning multiple formats: text, CSV, JSON, Python, and binary
placeholders (JPG, PDF, MP3, ZIP).

Run standalone:
    python setup_data.py [--output-dir ./test_dump] [--reset]
"""

import os
import json
import csv
import shutil
import argparse
from pathlib import Path
from datetime import datetime


# ─── Sample File Contents ─────────────────────────────────────────────────────

SAMPLE_FILES: dict = {
    "photo.jpg": None,  # Binary placeholder

    "script.py": '''\
#!/usr/bin/env python3
"""
Data processing utility — reads a CSV, filters high-value transactions,
and outputs a summary report.
"""

import csv

def process_transactions(filepath: str) -> list[dict]:
    """Filter transactions above threshold."""
    results = []
    with open(filepath, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if float(row.get("amount", 0)) > 100:
                results.append(row)
    return results

if __name__ == "__main__":
    data = process_transactions("transactions.csv")
    print(f"High-value transactions: {len(data)}")
    for txn in data[:5]:
        print(f"  {txn}")
''',

    "notes.txt": """\
Meeting Notes — Q4 Planning
============================
Date: 2024-12-01
Attendees: Alice, Bob, Carol

Agenda:
  1. Data pipeline architecture review
  2. MCP integration proposal
  3. Enterprise client demo scheduling
  4. Onboarding documentation update

Action Items:
  - Finalize data pipeline architecture       [Alice]
  - Review MCP integration proposal           [Bob]
  - Schedule demo with enterprise clients     [Carol]
  - Update onboarding docs                    [Alice, Carol]

Next meeting: 2024-12-15
""",

    "finance_info.txt": """\
Enterprise Finance Reference Sheet
====================================
Company:        Horizon Enterprises Ltd.
Account Number: 4521-8874-0091-2234
Bank:           Blockchain International Trust
Branch:         Hyderabad Main
IFSC Code:      BITI0001234
SWIFT Code:     BITSHYD123
Routing Number: 071000013
Contact:        treasury@horizon-ent.com

Payroll Schedule: 28th of each month
Revenue Q3 FY2024: $4,821,000
Tax Reference:  HYD-ENT-2024-TXN

⚠️  CONFIDENTIAL — Finance Department Only
   Do not distribute outside authorized personnel.
""",

    "data.csv": """\
id,name,department,salary,joining_date,performance_score
1,Alice Johnson,Engineering,120000,2021-03-15,4.8
2,Bob Smith,Finance,95000,2020-07-22,4.2
3,Carol White,Marketing,85000,2022-01-10,4.5
4,David Brown,Engineering,135000,2019-11-05,4.9
5,Eve Davis,HR,78000,2023-06-30,4.1
6,Frank Wilson,Finance,102000,2021-09-18,4.3
7,Grace Lee,Engineering,128000,2020-04-12,4.7
8,Henry Park,Marketing,91000,2022-08-25,4.0
9,Iris Chen,Data Science,145000,2021-01-20,4.9
10,James Kim,Engineering,118000,2023-02-14,4.4
""",

    "report.pdf": None,  # Binary placeholder

    "audio.mp3": None,  # Binary placeholder

    "config.json": json.dumps({
        "app": "Cascade",
        "version": "1.0.0",
        "description": "Agentic Data Ingestion Pipeline",
        "database": {
            "host": "localhost",
            "port": 5432,
            "name": "enterprise_db",
            "pool_size": 10
        },
        "pipeline": {
            "batch_size": 1000,
            "workers": 4,
            "retry_attempts": 3,
            "timeout_seconds": 30,
            "formats_supported": ["csv", "json", "pdf", "txt", "jpg", "mp3", "py", "zip"]
        },
        "llm": {
            "provider": "gemini",
            "model": "gemini-2.0-flash-exp",
            "temperature": 0.1,
            "max_tokens": 8192
        },
        "mcp": {
            "transport": "stdio",
            "server": "mcp_server.py"
        }
    }, indent=2),

    "archive.zip": None,  # Binary placeholder

    "requirements_snapshot.txt": """\
# Dependency snapshot — generated 2024-12-01
# Environment: Python 3.11.7 / Ubuntu 22.04

langchain==0.3.7
langchain-core==0.3.15
langchain-google-genai==2.0.4
langgraph==0.2.28
mcp==1.1.0
fastmcp==0.2.1
google-generativeai==0.8.3
python-dotenv==1.0.1

# Pinned for reproducibility
pydantic==2.9.2
httpx==0.27.2
""",
}


# ─── Binary Placeholder Headers ───────────────────────────────────────────────

BINARY_HEADERS: dict[str, bytes] = {
    ".jpg":  b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01",
    ".pdf":  b"%PDF-1.4\n%Sample Cascade PDF Placeholder\n",
    ".mp3":  b"ID3\x03\x00\x00\x00\x00\x00\x00",
    ".zip":  b"PK\x03\x04\x14\x00\x00\x00\x08\x00",
}


def _create_binary_placeholder(path: Path, header: bytes, size: int = 256):
    """Write a minimal binary placeholder file with realistic magic bytes."""
    content = header + bytes([0x00] * max(0, size - len(header)))
    path.write_bytes(content)


# ─── Main Functions ───────────────────────────────────────────────────────────

def seed_test_dump(output_dir: Path, reset: bool = False) -> Path:
    """
    Create or reset the test_dump directory with diverse sample files.

    Args:
        output_dir: Target directory path (will be created if needed).
        reset:      If True, wipe existing directory first.

    Returns:
        Path to the populated test_dump directory.
    """
    if reset and output_dir.exists():
        shutil.rmtree(output_dir)
        print(f"  🗑️  Wiped existing: {output_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'═'*60}")
    print(f"  Cascade — Test Data Seeder")
    print(f"{'═'*60}")
    print(f"\n  📁 Target: {output_dir}\n")

    created = 0
    for filename, content in SAMPLE_FILES.items():
        filepath = output_dir / filename
        ext = Path(filename).suffix.lower()

        if content is not None:
            filepath.write_text(content, encoding="utf-8")
        else:
            header = BINARY_HEADERS.get(ext, b"\x00" * 8)
            _create_binary_placeholder(filepath, header)

        size = filepath.stat().st_size
        print(f"  ✅ {filename:<35} {size:>6} bytes")
        created += 1

    print(f"\n  Total files created: {created}")
    print(f"\n{'─'*60}")
    print(f"  Directory ready for Cascade agent.")
    print(f"  Run: python cascade.py --demo")
    print(f"{'═'*60}\n")

    return output_dir


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="setup_data",
        description="Cascade — Seed test_dump/ with diverse sample files",
    )
    parser.add_argument(
        "--output-dir", "-o",
        type=str,
        default=None,
        help="Output directory path (default: <project_root>/test_dump)",
    )
    parser.add_argument(
        "--reset", "-r",
        action="store_true",
        help="Wipe and recreate the directory if it already exists",
    )
    args = parser.parse_args()

    if args.output_dir:
        output_dir = Path(args.output_dir).expanduser().resolve()
    else:
        # Default: project root / test_dump
        project_root = Path(__file__).parent
        output_dir   = project_root / "test_dump"

    seed_test_dump(output_dir, reset=args.reset)


if __name__ == "__main__":
    main()
