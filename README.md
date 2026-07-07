# Cascade — Agentic Data Ingestion Pipeline

This project is an **automated data ingestion pipeline** designed to unlock value from messy, unutilized corporate data. It automatically extracts, understands, and structures chaotic, multi-format files (like PDFs, logs, or emails) scattered across enterprise silos, turning them into clean, analytics-ready databases.

## Core Features
* **AI-Driven Parsing:** Uses autonomous agents (built with **LangGraph** and the Model Context Protocol) to contextually read unstructured documents and map them into strict, structured data schemas.
* **Privacy & Local First:** Features a simple Command Line Interface (CLI) that supports local LLM inference via **Ollama**, ensuring sensitive enterprise data never leaves your infrastructure.
* **Scalable Architecture:** Built with network-wide scalability in mind, using Server-Sent Events (SSE) transport to stream data efficiently across distributed environments.

---

## Architecture

```
╔═══════════════════════════════════════════════════════════════════════╗
║                Cascade — Agentic Data Ingestion Pipeline              ║
╠═══════════════════════════════════════════════════════════════════════╣
║                                                                       ║
║   User Query                                                          ║
║       │                                                               ║
║       ▼                                                               ║
║  ┌─────────────────────────┐         ┌──────────────────────────────┐ ║
║  │    cascade.py           │         │     mcp_server.py            │ ║
║  │  ─────────────────────  │         │   ──────────────────────     │ ║
║  │  LangGraph ReAct Agent  │◄──MCP──►│   FastMCP Tool Server        │ ║
║  │                         │  stdio  │                              │ ║
║  │  1. OBSERVE             │   or    │  • list_files                │ ║
║  │  2. ANALYZE             │   SSE   │  • read_file                 │ ║
║  │  3. EXECUTE             │         │  • move_file                 │ ║
║  │  4. SCHEMA              │         │  • get_file_metadata         │ ║
║  │  5. RETRIEVE            │         │  • search_content            │ ║
║  └─────────────────────────┘         │  • extract_schema ◄── NEW    │ ║
║          │                           └──────────────────────────────┘ ║
║          │                                         │                  ║
║          ▼                                         ▼                  ║
║  ┌───────────────────────────────┐      ┌────────────────────┐        ║
║  │   LLM Provider (your choice)  │      │  Local Filesystem  │        ║
║  │   ─────────────────────────── │      │  (test_dump/)      │        ║
║  │      Gemini 2.0 Flash (free)  │      │                    │        ║
║  │      Ollama / llama3 (local)  │      │  photo.jpg         │        ║
║  │      OpenAI GPT-4o-mini       │      │  data.csv          │        ║
║  │      Claude 3.5 Sonnet        │      │  finance_info.txt  │        ║
║  └───────────────────────────────┘      │  config.json  ...  │        ║
║                                         └────────────────────┘        ║
╚═══════════════════════════════════════════════════════════════════════╝
```

---

## Project Structure

```
cascade/
├── cascade.py          # Unified CLI entry-point (agent + all commands)
├── mcp_server.py       # FastMCP Tool Server (6 tools)
├── setup_data.py       # Seeds test_dump/ with sample multi-format files
├── run.sh              # Convenience shell wrapper
├── requirements.txt    # All dependencies (all 4 LLM providers)
├── .env.example        # API key template
└── README.md
```

---

## Quick Start

### 1. Clone & Enter

```bash
git clone <repo-url> cascade
cd cascade
```

### 2. Create Virtual Environment & Install

```bash
# Using uv (recommended — fast)
uv venv .venv && source .venv/bin/activate
uv pip install -r requirements.txt

# OR standard pip
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# OR using the run script
./run.sh setup
```

### 3. Configure API Key

```bash
cp .env.example .env
# Edit .env and set the key for your chosen provider
```

> **Using Ollama?** No API key needed. [Install Ollama](https://ollama.com/download) and run `ollama pull llama3`.

### 4. Run

```bash
# Gemini (default)
./run.sh demo

# Local Ollama — no API key, fully private
./run.sh demo --llm ollama

# OpenAI
./run.sh demo --llm openai

# Anthropic Claude
./run.sh demo --llm claude
```

---

## LLM Provider Selection

| Provider | Flag | Default Model | API Key Needed |
|---|---|---|---|
| **Google Gemini** | `--llm gemini` | `gemini-2.0-flash-exp` | `GEMINI_API_KEY` ([free](https://aistudio.google.com/apikey)) |
| **Ollama (local)** | `--llm ollama` | `llama3` | ❌ None — runs locally |
| **OpenAI** | `--llm openai` | `gpt-4o-mini` | `OPENAI_API_KEY` |
| **Anthropic Claude** | `--llm claude` | `claude-3-5-sonnet-20241022` | `ANTHROPIC_API_KEY` |

Override any model with `--model <name>`:

```bash
python cascade.py --llm ollama --model llama3.1 --demo
python cascade.py --llm openai --model gpt-4o --demo
python cascade.py --llm gemini --model gemini-1.5-pro --demo
```

### Ollama Setup

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model
ollama pull llama3          # 4.7 GB — general purpose
ollama pull mistral         # 4.1 GB — fast & capable
ollama pull qwen2.5:7b      # good tool-calling support

# Run Cascade with Ollama
python cascade.py --llm ollama --model llama3 --demo
```

---

## CLI Reference

```
python cascade.py [MODE] [LLM OPTIONS] [AGENT OPTIONS] [TRANSPORT OPTIONS]
```

### Modes

| Flag | Description |
|---|---|
| *(default)* | Run agent pipeline |
| `--demo` | Run on seeded `test_dump/` with a SWIFT code query |
| `--setup` | Populate `test_dump/` with sample files |
| `--check` | Verify LLM connectivity and exit |
| `--serve` | Start MCP server over SSE for remote access |

### Full Usage

```bash
# Demo run (seeds test_dump if missing)
python cascade.py --demo

# Custom directory and query
python cascade.py \
  --directory ./my-data \
  --query "Organize these files and find any SWIFT codes" \
  --llm gemini \
  --verbose

# Test LLM connectivity
python cascade.py --check --llm ollama

# Seed sample test data (reset if it exists)
python cascade.py --setup --reset

# Start MCP server for network-wide access
python cascade.py --serve --sse-port 8000

# Connect agent to remote MCP server
python cascade.py \
  --transport sse \
  --sse-host 192.168.1.100 \
  --sse-port 8000 \
  --demo
```

### `run.sh` Shortcuts

```bash
./run.sh setup              # venv + pip install
./run.sh seed               # populate test_dump/
./run.sh demo               # full demo (Gemini)
./run.sh demo --llm ollama  # full demo (local)
./run.sh check              # LLM connectivity check
./run.sh serve              # SSE MCP server on :8000
./run.sh reset              # wipe + reseed test_dump/
./run.sh run ./data "Find all invoices"  # custom run
```

---

## MCP Tools Reference

The `mcp_server.py` server exposes **6 tools** via FastMCP:

| Tool | Description |
|---|---|
| `list_files(directory)` | Lists all files with sizes, categories, and readability flags |
| `read_file(filename, directory)` | Reads text content; CSV gets structured preview; binary files return metadata |
| `move_file(filename, source_dir, category)` | Moves file into category subfolder (auto-creates dirs, handles collisions) |
| `get_file_metadata(filename, directory)` | Returns size, timestamps, extension, and category hint as JSON |
| `search_content(directory, keyword)` | Full-text search across all readable files with line-level hits |
| `extract_schema(directory)` | **Produces machine-readable JSON inventory schema** of the entire data silo |

### `extract_schema` Output

The `extract_schema` tool is the core deliverable — it converts an unstructured file dump into a **structured, analytics-ready JSON schema**:

```json
{
  "cascade_schema_version": "1.0",
  "directory": "/path/to/test_dump",
  "generated_at": "2024-12-01T14:32:01",
  "total_files": 9,
  "category_summary": {
    "Code":    { "count": 1, "files": ["script.py"] },
    "Config":  { "count": 1, "files": ["config.json"] },
    "Data":    { "count": 1, "files": ["data.csv"] },
    "Docs":    { "count": 2, "files": ["notes.txt", "requirements_snapshot.txt"] },
    "Finance": { "count": 1, "files": ["finance_info.txt"] },
    "Media":   { "count": 2, "files": ["audio.mp3", "photo.jpg"] },
    "Archives":{ "count": 1, "files": ["archive.zip"] }
  },
  "files": [
    {
      "filename": "finance_info.txt",
      "category": "Finance",
      "size_bytes": 412,
      "is_readable": true,
      "finance_signals": true,
      "content_preview": "Enterprise Finance Reference Sheet ...",
      "extracted_keys": [],
      "modified": "2024-12-01T14:30:00"
    },
    {
      "filename": "data.csv",
      "category": "Data",
      "size_bytes": 390,
      "is_readable": true,
      "finance_signals": false,
      "extracted_keys": ["id", "name", "department", "salary", "joining_date", "performance_score"],
      "modified": "2024-12-01T14:30:00"
    }
  ]
}
```

---

## Sample Agent Interaction

**Query:** `"Organize all the files and tell me the bank's SWIFT code"`

```
╔═══════════════════════════════════════════════════════════════╗
║  Cascade — Agentic Data Ingestion Pipeline                    ║
╚═══════════════════════════════════════════════════════════════╝

  Target Directory : /home/user/cascade/test_dump
  User Query       : Organize all files and tell me the bank's SWIFT code
  LLM Provider     : GEMINI (gemini-2.0-flash-exp)
  Agent Framework  : LangGraph ReAct + FastMCP
  MCP Transport    : STDIO

─────────────────────────────────────────────────────────────────
  Agent Reasoning Loop Starting...
─────────────────────────────────────────────────────────────────

💭 Agent Thought:
   I need to observe the directory contents first before organizing anything.

🔧 Tool: list_files
   directory: '/path/to/test_dump'

   ↳ Result:
   📁 Directory: /path/to/test_dump
      Files: 9  |  Subdirectories: 0
   ──────────────────────────────────────────────────────
     📄 archive.zip               0.3 KB  [Archives]   readable:✗
     📄 audio.mp3                 0.3 KB  [Media   ]   readable:✗
     📄 config.json               0.5 KB  [Config  ]   readable:✓
     📄 data.csv                  0.4 KB  [Data    ]   readable:✓
     📄 finance_info.txt          0.4 KB  [Docs    ]   readable:✓
     📄 notes.txt                 0.3 KB  [Docs    ]   readable:✓
     📄 photo.jpg                 0.3 KB  [Media   ]   readable:✗
     📄 requirements_snapshot.txt 0.4 KB  [Docs    ]   readable:✓
     📄 script.py                 0.6 KB  [Code    ]   readable:✓

💭 Agent Thought:
   finance_info.txt is categorized as Docs but the name suggests Finance.
   I must read it to confirm the category and find the SWIFT code.

🔧 Tool: read_file
   filename: 'finance_info.txt'  directory: '/path/to/test_dump'

   ↳ Result:
   Enterprise Finance Reference Sheet
   ====================================
   SWIFT Code: BITSHYD123
   Bank: Blockchain International Trust
   ...

💭 Agent Thought:
   Found SWIFT Code: BITSHYD123. This file must go to Finance category.
   Now I'll systematically move all 9 files.

🔧 Tool: move_file  (photo.jpg → Media)      ✅
🔧 Tool: move_file  (audio.mp3 → Media)      ✅
🔧 Tool: move_file  (script.py → Code)       ✅
🔧 Tool: move_file  (data.csv → Data)        ✅
🔧 Tool: move_file  (config.json → Config)   ✅
🔧 Tool: move_file  (notes.txt → Docs)       ✅
🔧 Tool: move_file  (requirements_snapshot.txt → Docs) ✅
🔧 Tool: move_file  (archive.zip → Archives) ✅
🔧 Tool: move_file  (finance_info.txt → Finance) ✅

🔧 Tool: extract_schema
   directory: '/path/to/test_dump'

   ↳ Result: (JSON schema with 9 file records, category summary,
              finance signals detected, CSV column names extracted)

═══════════════════════════════════════════════════════════════
Final Response:
═══════════════════════════════════════════════════════════════

I've organized all 9 files into structured categories:

  📁 Media/    → photo.jpg, audio.mp3
  📁 Code/     → script.py
  📁 Data/     → data.csv
  📁 Config/   → config.json
  📁 Docs/     → notes.txt, requirements_snapshot.txt
  📁 Archives/ → archive.zip
  📁 Finance/  → finance_info.txt

🏦 Your bank's SWIFT code is:  BITSHYD123
   Bank: Blockchain International Trust, Hyderabad Main

A structured JSON schema of the entire directory has been generated
and is available via the extract_schema tool output.

✅ Cascade session complete.
```

---

## Network-Wide Scalability (SSE Transport)

Deploy the MCP server as a network service — any machine on your network can then connect agents to it:

**Server machine:**
```bash
# Start MCP server over SSE
python mcp_server.py --sse --host 0.0.0.0 --port 8000
# or
./run.sh serve
```

**Client machines:**
```bash
python cascade.py \
  --transport sse \
  --sse-host 192.168.1.100 \
  --sse-port 8000 \
  --llm ollama \
  --directory /mnt/enterprise-data \
  --query "Extract all financial records and produce a structured schema"
```

This enables enterprise-scale deployment where a single MCP server can serve multiple concurrent agent sessions across different machines.

---

## Key Design Decisions

| Decision | Rationale |
|---|---|
| **FastMCP over raw MCP** | Declarative `@mcp.tool()` decorators eliminate boilerplate; automatic schema inference |
| **LangGraph ReAct loop** | Transparent step-by-step reasoning with full tool call history — debuggable and auditable |
| **Content-aware categorization** | Files analyzed by both extension AND content keywords (finance signals, code patterns) |
| **`extract_schema` tool** | Converts raw file dumps into structured JSON inventory — the "analytics-ready" deliverable |
| **Multi-provider LLM** | Gemini free tier for accessibility; Ollama for air-gapped/private deployments; Claude/OpenAI for power users |
| **stdio + SSE transports** | stdio for local single-machine use; SSE for network-wide multi-agent deployments |
| **Graceful binary handling** | Images/audio/archives return metadata instead of crashing — robust against mixed-format silos |
| **Argparse CLI** | Standard, composable flags — scriptable from CI/CD or shell pipelines |

---

## 📜 License

MIT — Free to use, modify, and deploy for educational and enterprise purposes.
