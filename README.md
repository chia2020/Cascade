# Cascade — Agentic Data Ingestion Pipeline

Cascade is an autonomous data organization and schema-synthesis pipeline designed to eliminate manual file system clutter and process unorganized data dumps. 

I built this originally to automate my desktop decluttering of files and folders without writing rigid rule-based scripts, Cascade uses **LangGraph** and the **Model Context Protocol (MCP)** to inspect file contents semantically, clean up raw directories, and extract analytics-ready metadata schemas.

This is engineered with enterprise deployment in mind, Cascade supports air-gapped execution via **Ollama**, path-traversal security sandboxing, multi-node scalability over **Server-Sent Events (SSE)**, and pluggable support for major cloud LLMs.

---

## Core Capabilities

* **Content-Aware File Triage:** Sorts messy directories based on actual file content and financial/code signals, bypassing misleading extensions.
* **Enterprise Dark Data Ingestion:** Converts unstructured corporate dumps (logs, CSVs, code, text, binary media) into structured JSON inventory schemas via the `extract_schema` tool.
* **Built-in Security & Privacy:** Features strict root-directory sandboxing and path traversal (`../`) checks to prevent unauthorized file access, alongside local **Ollama** support for 100% air-gapped processing.
* **Scalable Architecture:** Built on FastMCP with dual transport modes (`stdio` for local CLI execution and `SSE` for distributed multi-node server deployments).
* **Multi-LLM Support:** Direct flags to swap between Google Gemini, local Ollama models (Llama 3, Qwen, Mistral), OpenAI, and Anthropic Claude.

---

## Architecture Overview

```
+-----------------------------------------------------------------------+
|                Cascade — Agentic Data Ingestion Pipeline              |
+-----------------------------------------------------------------------+
|                                                                       |
|   User Query / Automated Trigger                                      |
|        |                                                              |
|        v                                                              |
|   +-------------------------+         +------------------------------+ |
|   |    cascade.py           |         |     mcp_server.py            | |
|   |  ---------------------  |         |   ----------------------     | |
|   |  LangGraph ReAct Agent  |<--MCP-->|    FastMCP Tool Server       | |
|   |                         |  stdio  |                              | |
|   |  1. OBSERVE             |   or    |   • list_files               | |
|   |  2. ANALYZE             |   SSE   |   • read_file                | |
|   |  3. EXECUTE             |         |   • move_file                | |
|   |  4. SCHEMA              |         |   • get_file_metadata        | |
|   |  5. RETRIEVE            |         |   • search_content           | |
|   +-------------------------+         |   • extract_schema           | |
|            |                          +------------------------------+ |
|            |                                         |                 |
|            v                                         v                 |
|   +-------------------------------+         +--------------------+    |
|   |   LLM Provider (Pluggable)    |         |  Target Directory  |    |
|   |   --------------------------- |         |  (Sandboxed Path)  |    |
|   |    Ollama (Llama 3 / Qwen)    |         |                    |    |
|   |    Google Gemini 2.0 Flash    |         |   photo.jpg        |    |
|   |    OpenAI GPT-4o-mini         |         |   data.csv         |    |
|   |    Anthropic Claude 3.5       |         |   finance_info.txt |    |
|   +-------------------------------+         +--------------------+    |
+-----------------------------------------------------------------------+
```

---

## Repository Structure

```
cascade/
├── cascade.py          # Unified CLI entry-point & LangGraph ReAct agent loop
├── mcp_server.py       # FastMCP Tool Server with security & validation hooks
├── setup_data.py       # Utility to populate test_dump/ with sample data
├── run.sh              # Shell wrapper for setup, execution, and serving
├── requirements.txt    # Project dependencies
├── .env.example        # Environment variable template
└── README.md           # Project documentation
```

## Security Model

Because Cascade executes real file-system operations driven by LLM decisions, security is enforced at the server layer rather than relying on prompt instructions:

1. **Path Normalization & Jailbreak Prevention:** All file paths received by `mcp_server.py` are resolved using absolute paths (`os.path.abspath`) and verified against the target directory root. Requests referencing parent paths (`../`) or system root are blocked.
2. **Safe Handling of Untrusted Files:** Non-text files, binary blobs, and large archives are intercepted safely—metadata is returned without attempting raw memory loading or script execution.
3. **Air-Gapped Data Privacy:** Local execution via Ollama ensures data never transmits over external APIs or leaves private networks.

---

## Quick Start Guide

### 1. Installation

```bash
git clone [https://github.com/your-username/cascade.git](https://github.com/your-username/cascade.git)
cd cascade

# Using uv (Recommended)
uv venv .venv && source .venv/bin/activate
uv pip install -r requirements.txt

# Or standard pip
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

```

### 2. Configuration

```bash
cp .env.example .env
# Add API keys if using cloud providers (Gemini, OpenAI, Claude).
# No key required for Ollama local inference.

```

### 3. Running Cascade

```bash
# Default demo (Gemini)
./run.sh demo

# 100% Local & Private (Ollama)
./run.sh demo --llm ollama

# Cloud Providers
./run.sh demo --llm openai
./run.sh demo --llm claude

```

---

## MCP Tools Reference

The `mcp_server.py` server exposes **6 core tools** via FastMCP:

| Tool | Description |
| --- | --- |
| `list_files(directory)` | Lists directory contents, sizes, category hints, and readability flags. |
| `read_file(filename, directory)` | Context-aware reader: returns text lines, CSV head previews, or binary metadata. |
| `move_file(filename, source_dir, category)` | Relocates files safely; handles folder creation and prevents name collisions. |
| `get_file_metadata(filename, directory)` | Retrieves detailed timestamps, file size, extensions, and structural signals. |
| `search_content(directory, keyword)` | Line-by-line full-text search across all readable contents. |
| `extract_schema(directory)` | **Generates a machine-readable JSON inventory schema** for database ingestion. |

---

## Network Deployment (SSE Transport)

Cascade can run as a centralized MCP service across a network:

**Host Node (Data Storage):**

```bash
python cascade.py --serve --sse-port 8000

```

**Client / Worker Node:**

```bash
python cascade.py \
  --transport sse \
  --sse-host 192.168.1.100 \
  --sse-port 8000 \
  --directory /mnt/enterprise-silo \
  --llm ollama \
  --query "Organize directory and output structured schema"

```

---

## License

MIT License — Free to use, modify, and deploy.

```

```
