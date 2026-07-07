"""
Cascade — Agentic Data Ingestion Pipeline
==========================================
Single unified entry point for the Cascade project.

Enabled analytics on 50%+ of unutilized enterprise data by orchestrating
a LangGraph ReAct agent over a FastMCP tool server to contextually parse
multi-format unstructured data silos and convert them into structured schemas.

Supports four LLM providers:
  gemini  — Google Gemini 2.0 Flash (default, free)
  openai  — OpenAI GPT-4o-mini
  claude  — Anthropic Claude 3.5 Sonnet
  ollama  — Local Ollama (no API key required)

MCP transports:
  stdio   — default, subprocess-based local communication
  sse     — HTTP/SSE for network-wide deployment

Usage:
  python cascade.py --demo
  python cascade.py --llm ollama --demo
  python cascade.py --llm openai --directory ./data --query "Summarize everything"
  python cascade.py --check --llm gemini
  python cascade.py --setup
  python cascade.py --serve --transport sse --port 8000
"""

import os
import sys
import json
import asyncio
import argparse
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).parent


# ─── ANSI Color Helpers ───────────────────────────────────────────────────────

class C:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    CYAN    = "\033[96m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    MAGENTA = "\033[95m"
    RED     = "\033[91m"
    WHITE   = "\033[97m"


def _print_banner():
    lines = [
        "╔═══════════════════════════════════════════════════════════════╗",
        "║                                                               ║",
        "║    ██████╗ █████╗ ███████╗ ██████╗ █████╗ ██████╗ ███████╗  ║",
        "║   ██╔════╝██╔══██╗██╔════╝██╔════╝██╔══██╗██╔══██╗██╔════╝  ║",
        "║   ██║     ███████║███████╗██║     ███████║██║  ██║█████╗    ║",
        "║   ██║     ██╔══██║╚════██║██║     ██╔══██║██║  ██║██╔══╝    ║",
        "║   ╚██████╗██║  ██║███████║╚██████╗██║  ██║██████╔╝███████╗  ║",
        "║    ╚═════╝╚═╝  ╚═╝╚══════╝ ╚═════╝╚═╝  ╚═╝╚═════╝ ╚══════╝  ║",
        "║                                                               ║",
        "║         Agentic Data Ingestion Pipeline  v1.0.0              ║",
        "║      LangGraph · MCP · Multi-LLM · Network-Scale             ║",
        "╚═══════════════════════════════════════════════════════════════╝",
    ]
    print(f"\n{C.CYAN}{C.BOLD}")
    for line in lines:
        print(f"  {line}")
    print(C.RESET)


def _banner(title: str, char: str = "═", width: int = 65):
    pad = (width - len(title) - 2) // 2
    print(f"\n{C.CYAN}{C.BOLD}{char*width}{C.RESET}")
    print(f"{C.CYAN}{C.BOLD}{char*pad} {title} {char*pad}{C.RESET}")
    print(f"{C.CYAN}{C.BOLD}{char*width}{C.RESET}\n")


def _thought(text: str):
    print(f"\n{C.YELLOW}💭 Agent Thought:{C.RESET}")
    for line in text.strip().split("\n"):
        print(f"   {C.YELLOW}{line}{C.RESET}")


def _action_header(tool_name: str, args: dict):
    print(f"\n{C.GREEN}🔧 Tool: {C.BOLD}{tool_name}{C.RESET}")
    for k, v in args.items():
        print(f"   {C.DIM}{k}: {v!r}{C.RESET}")


def _tool_result(result_text: str, max_lines: int = 20):
    print(f"\n{C.GREEN}   ↳ Result:{C.RESET}")
    lines = result_text.splitlines()
    for line in lines[:max_lines]:
        print(f"   {C.DIM}{line}{C.RESET}")
    if len(lines) > max_lines:
        print(f"   {C.DIM}... (+{len(lines)-max_lines} more lines){C.RESET}")


def _final_response(text: str):
    print(f"\n{C.MAGENTA}{C.BOLD}{'═'*65}{C.RESET}")
    print(f"{C.MAGENTA}{C.BOLD}  🎯 Final Response:{C.RESET}")
    print(f"{C.MAGENTA}{C.BOLD}{'═'*65}{C.RESET}")
    print(f"\n{C.MAGENTA}{text}{C.RESET}\n")


# ─── Dependency Check ─────────────────────────────────────────────────────────

PROVIDER_DEPS = {
    "gemini": [("langchain-google-genai", "langchain_google_genai")],
    "openai": [("langchain-openai",       "langchain_openai")],
    "claude": [("langchain-anthropic",    "langchain_anthropic")],
    "ollama": [("langchain-ollama",       "langchain_ollama")],
}

COMMON_DEPS = [
    ("langchain",     "langchain"),
    ("langchain-core","langchain_core"),
    ("langgraph",     "langgraph"),
    ("mcp",           "mcp"),
]


def _check_deps(llm_provider: str):
    """Check all required packages are installed."""
    missing = []
    all_deps = COMMON_DEPS + PROVIDER_DEPS.get(llm_provider, [])
    for pkg, imp in all_deps:
        try:
            __import__(imp)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"{C.RED}ERROR: Missing packages: {', '.join(missing)}{C.RESET}")
        print(f"  Run: pip install {' '.join(missing)}")
        sys.exit(1)


# ─── LLM Factory ─────────────────────────────────────────────────────────────

def _build_llm(provider: str, model: Optional[str], ollama_url: str):
    """Instantiate the correct LangChain chat model for the chosen provider."""

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print(f"{C.RED}ERROR: GEMINI_API_KEY not set.{C.RESET}")
            print("  Get a free key at https://aistudio.google.com/apikey")
            print("  Then: export GEMINI_API_KEY=your_key   (or add to .env)")
            sys.exit(1)
        return ChatGoogleGenerativeAI(
            model=model or "gemini-2.0-flash-exp",
            google_api_key=api_key,
            temperature=0.1,
            convert_system_message_to_human=True,
        ), model or "gemini-2.0-flash-exp"

    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print(f"{C.RED}ERROR: OPENAI_API_KEY not set.{C.RESET}")
            print("  Get a key at https://platform.openai.com/api-keys")
            print("  Then: export OPENAI_API_KEY=your_key   (or add to .env)")
            sys.exit(1)
        return ChatOpenAI(
            model=model or "gpt-4o-mini",
            api_key=api_key,
            temperature=0.1,
        ), model or "gpt-4o-mini"

    elif provider == "claude":
        from langchain_anthropic import ChatAnthropic
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            print(f"{C.RED}ERROR: ANTHROPIC_API_KEY not set.{C.RESET}")
            print("  Get a key at https://console.anthropic.com/")
            print("  Then: export ANTHROPIC_API_KEY=your_key   (or add to .env)")
            sys.exit(1)
        return ChatAnthropic(
            model=model or "claude-3-5-sonnet-20241022",
            api_key=api_key,
            temperature=0.1,
        ), model or "claude-3-5-sonnet-20241022"

    elif provider == "ollama":
        from langchain_ollama import ChatOllama
        ollama_model = model or os.getenv("OLLAMA_MODEL", "llama3")
        base_url     = ollama_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        print(f"{C.DIM}  Connecting to Ollama at {base_url} (model: {ollama_model})...{C.RESET}")
        return ChatOllama(
            model=ollama_model,
            base_url=base_url,
            temperature=0.1,
        ), f"ollama/{ollama_model}"

    else:
        print(f"{C.RED}ERROR: Unknown LLM provider '{provider}'.{C.RESET}")
        print("  Choose from: gemini, openai, claude, ollama")
        sys.exit(1)


# ─── LLM Connectivity Check ───────────────────────────────────────────────────

def cmd_check(args):
    """Run a quick connectivity test against the selected LLM provider."""
    _check_deps(args.llm)
    llm, model_name = _build_llm(args.llm, args.model, args.ollama_url)

    from langchain_core.messages import HumanMessage
    _banner("Cascade — LLM Connectivity Check")
    print(f"  Provider : {args.llm.upper()}")
    print(f"  Model    : {model_name}")
    print(f"\n  Sending test prompt...\n")

    prompt = (
        "You are an expert data engineer. In exactly 3 bullet points, "
        "explain why agentic data pipelines powered by LLM agents are "
        "transforming enterprise data management."
    )
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        text = response.content if hasattr(response, "content") else str(response)
        print(f"{C.GREEN}{'─'*65}{C.RESET}")
        print(f"{C.GREEN}  Response from {model_name}:{C.RESET}")
        print(f"{C.GREEN}{'─'*65}{C.RESET}")
        print(f"\n{text}\n")
        print(f"{C.GREEN}✅ LLM connectivity check passed!{C.RESET}\n")
    except Exception as e:
        print(f"{C.RED}❌ LLM check failed: {e}{C.RESET}\n")
        sys.exit(1)


# ─── Test Data Setup ──────────────────────────────────────────────────────────

def cmd_setup(args):
    """Seed test_dump/ with sample multi-format files."""
    seeder = ROOT / "setup_data.py"
    if not seeder.exists():
        print(f"{C.RED}ERROR: setup_data.py not found at {seeder}{C.RESET}")
        sys.exit(1)

    output_dir = Path(args.directory).expanduser().resolve() if args.directory else ROOT / "test_dump"

    # Import inline to avoid circular deps
    import importlib.util
    spec = importlib.util.spec_from_file_location("setup_data", seeder)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.seed_test_dump(output_dir, reset=args.reset)


# ─── MCP Server (Serve Mode) ──────────────────────────────────────────────────

def cmd_serve(args):
    """Start the MCP server in SSE mode for network-wide access."""
    server_script = ROOT / "mcp_server.py"
    if not server_script.exists():
        print(f"{C.RED}ERROR: mcp_server.py not found.{C.RESET}")
        sys.exit(1)

    _banner("Cascade — MCP Server (SSE Mode)")
    print(f"  Host : {args.sse_host}")
    print(f"  Port : {args.sse_port}")
    print(f"  URL  : http://{args.sse_host}:{args.sse_port}/sse")
    print(f"\n  Connect remote agents with:")
    print(f"  {C.DIM}python cascade.py --transport sse --sse-host <server-ip> --sse-port {args.sse_port} --demo{C.RESET}\n")

    import subprocess
    subprocess.run([
        sys.executable, str(server_script),
        "--sse",
        "--host", args.sse_host,
        "--port", str(args.sse_port),
    ])


# ─── Agent System Prompt ──────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are Cascade, an expert Agentic Data Ingestion Agent. Your mission is to
unlock analytics on unstructured enterprise data silos by autonomously
organizing, reading, and extracting structured information from files.

## Your Reasoning Loop (always follow this order):

1. OBSERVE   — Call list_files to see the full contents of the target directory
2. ANALYZE   — Call read_file on any ambiguous or text-based files to understand content
3. EXECUTE   — Call move_file to organize EVERY file into appropriate category subfolders:
               • Media    → images (.jpg, .png) and audio (.mp3, .wav)
               • Code     → scripts (.py, .js, .sh), web files (.html, .css)
               • Data     → structured data (.csv, .json, .xml)
               • Finance  → detect via content: SWIFT, IBAN, salary, invoice, payroll
               • Docs     → documentation (.txt, .md, .pdf)
               • Archives → compressed files (.zip, .tar, .gz)
               • Config   → config files (.ini, .cfg, .env, .json configs)
4. SCHEMA    — Call extract_schema on the directory to produce the structured JSON inventory
5. RETRIEVE  — Answer the user's specific question using information found during analysis

## Rules:
- Always call list_files FIRST
- Read text files before moving them — content determines category for .txt files
- Move EVERY file — leave nothing uncategorized
- Explicitly call out any specific data the user asked for (SWIFT codes, emails, etc.)
- After organizing, always call extract_schema to generate the structured data output
- Provide a clear final summary: what was moved where, and the answer to the user's query

Target directory: {directory}
LLM Provider: {provider}
"""


# ─── Core Agent Runner ────────────────────────────────────────────────────────

async def _run_agent(
    directory: str,
    query: str,
    llm,
    model_name: str,
    provider: str,
    verbose: bool,
    transport: str,
    sse_host: str,
    sse_port: int,
):
    from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
    from langchain_core.tools import StructuredTool
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    dir_path = Path(directory).expanduser().resolve()
    if not dir_path.exists():
        print(f"{C.RED}ERROR: Directory not found: {dir_path}{C.RESET}")
        sys.exit(1)

    server_script = ROOT / "mcp_server.py"
    if not server_script.exists():
        print(f"{C.RED}ERROR: mcp_server.py not found at {server_script}{C.RESET}")
        sys.exit(1)

    # ── Session info printout ──
    _banner("Cascade — Agentic Data Ingestion Pipeline")
    print(f"  {C.BOLD}Target Directory :{C.RESET} {dir_path}")
    print(f"  {C.BOLD}User Query       :{C.RESET} {query}")
    print(f"  {C.BOLD}LLM Provider     :{C.RESET} {provider.upper()} ({model_name})")
    print(f"  {C.BOLD}Agent Framework  :{C.RESET} LangGraph ReAct + FastMCP")
    print(f"  {C.BOLD}MCP Transport    :{C.RESET} {transport.upper()}")
    print()

    # ── Establish MCP connection ──
    if transport == "sse":
        from mcp.client.sse import sse_client
        sse_url = f"http://{sse_host}:{sse_port}/sse"
        print(f"{C.DIM}  Connecting to remote MCP server: {sse_url}...{C.RESET}\n")
        ctx = sse_client(sse_url)
    else:
        server_params = StdioServerParameters(
            command=sys.executable,
            args=[str(server_script)],
            env=None,
        )
        print(f"{C.DIM}  Starting MCP server: mcp_server.py (stdio)...{C.RESET}\n")
        ctx = stdio_client(server_params)

    async with ctx as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools_response = await session.list_tools()
            tool_names = [t.name for t in tools_response.tools]
            print(f"{C.DIM}  MCP Tools: {', '.join(tool_names)}{C.RESET}")

            print(f"\n{C.CYAN}{'─'*65}{C.RESET}")
            print(f"{C.CYAN}{C.BOLD}  🤖 Agent Reasoning Loop Starting...{C.RESET}")
            print(f"{C.CYAN}{'─'*65}{C.RESET}")

            # ── Build message history ──
            messages = [
                SystemMessage(content=SYSTEM_PROMPT.format(
                    directory=str(dir_path),
                    provider=provider.upper(),
                )),
                HumanMessage(content=query),
            ]

            max_steps = 30
            step_num  = 0

            while step_num < max_steps:
                step_num += 1

                # ── Build LangChain tool wrappers per step ──
                lc_tools = []
                for mcp_tool_def in tools_response.tools:
                    tname = mcp_tool_def.name

                    def _make_tool(captured_name: str, captured_session: ClientSession):
                        async def _async_call(**kwargs):
                            if "directory" in kwargs and not kwargs.get("directory"):
                                kwargs["directory"] = str(dir_path)
                            if "source_dir" in kwargs and not kwargs.get("source_dir"):
                                kwargs["source_dir"] = str(dir_path)
                            result = await captured_session.call_tool(
                                captured_name, arguments=kwargs
                            )
                            texts = [b.text for b in result.content if hasattr(b, "text")]
                            return "\n".join(texts) if texts else "(no output)"

                        def _sync_call(**kwargs):
                            loop = asyncio.get_event_loop()
                            return loop.run_until_complete(_async_call(**kwargs))

                        return StructuredTool.from_function(
                            func=_sync_call,
                            name=captured_name,
                            description=(mcp_tool_def.description or captured_name),
                            return_direct=False,
                        )

                    lc_tools.append(_make_tool(tname, session))

                llm_with_tools = llm.bind_tools(lc_tools)

                if verbose:
                    print(f"\n{C.DIM}  [Step {step_num}] Invoking LLM ({len(messages)} messages in context)...{C.RESET}")

                # ── LLM call ──
                response = llm_with_tools.invoke(messages)
                messages.append(response)

                # ── No tool calls → agent is done ──
                if not response.tool_calls:
                    _final_response(response.content)
                    break

                # ── Print agent's reasoning ──
                if response.content:
                    _thought(response.content)

                # ── Execute each tool call via MCP ──
                for tc in response.tool_calls:
                    tool_name = tc["name"]
                    tool_args = tc["args"]

                    # Inject directory defaults
                    if "directory" in tool_args and not tool_args.get("directory"):
                        tool_args["directory"] = str(dir_path)
                    if "source_dir" in tool_args and not tool_args.get("source_dir"):
                        tool_args["source_dir"] = str(dir_path)

                    _action_header(tool_name, tool_args)

                    try:
                        mcp_result = await session.call_tool(tool_name, arguments=tool_args)
                        texts = [b.text for b in mcp_result.content if hasattr(b, "text")]
                        result_text = "\n".join(texts) if texts else "(no output)"
                    except Exception as e:
                        result_text = f"TOOL ERROR: {e}"

                    _tool_result(result_text)

                    messages.append(ToolMessage(
                        content=result_text,
                        tool_call_id=tc["id"],
                    ))

            if step_num >= max_steps:
                print(f"\n{C.RED}⚠️  Reached maximum step limit ({max_steps}).{C.RESET}")

    print(f"\n{C.CYAN}{'═'*65}{C.RESET}")
    print(f"{C.CYAN}{C.BOLD}  ✅ Cascade session complete.{C.RESET}")
    print(f"{C.CYAN}{'═'*65}{C.RESET}\n")


def cmd_run(args):
    """Main entry point for the agent pipeline."""
    _check_deps(args.llm)
    llm, model_name = _build_llm(args.llm, args.model, args.ollama_url)

    if args.demo or args.directory is None:
        directory = str(ROOT / "test_dump")
        query     = args.query or "Organize all the files and tell me the bank's SWIFT code"
        verbose   = True
        if not Path(directory).exists():
            print(f"{C.YELLOW}  test_dump/ not found — seeding it now...{C.RESET}\n")
            from setup_data import seed_test_dump
            seed_test_dump(Path(directory))
        else:
            print(f"{C.YELLOW}  Demo mode: using existing test_dump/  (run --setup --reset to refresh){C.RESET}\n")
    else:
        directory = args.directory
        query     = args.query or "Organize all the files and extract a structured schema"
        verbose   = args.verbose

    asyncio.run(_run_agent(
        directory  = directory,
        query      = query,
        llm        = llm,
        model_name = model_name,
        provider   = args.llm,
        verbose    = verbose,
        transport  = args.transport,
        sse_host   = args.sse_host,
        sse_port   = args.sse_port,
    ))


# ─── CLI ──────────────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cascade",
        description=(
            "Cascade — Agentic Data Ingestion Pipeline\n"
            "  Autonomously organize multi-format file dumps and convert\n"
            "  unstructured enterprise data into structured schemas using\n"
            "  LangGraph + MCP with your choice of LLM provider."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
LLM Providers:
  gemini  — Google Gemini 2.0 Flash  (needs GEMINI_API_KEY)
  openai  — OpenAI GPT-4o-mini       (needs OPENAI_API_KEY)
  claude  — Anthropic Claude 3.5     (needs ANTHROPIC_API_KEY)
  ollama  — Local Ollama             (no API key — install from ollama.com)

Examples:
  python cascade.py --demo
  python cascade.py --llm ollama --demo
  python cascade.py --llm openai --directory ./data --query "Summarize and organize"
  python cascade.py --llm claude --directory ~/downloads --query "Find all finance docs"
  python cascade.py --check --llm gemini
  python cascade.py --setup --reset
  python cascade.py --serve --sse-port 8000
""",
    )

    # ── Mode flags ──
    modes = parser.add_argument_group("Modes (pick one)")
    mode_x = modes.add_mutually_exclusive_group()
    mode_x.add_argument("--demo",  action="store_true",
                        help="Run agent on default test_dump/ with SWIFT query")
    mode_x.add_argument("--setup", action="store_true",
                        help="Seed test_dump/ with sample files and exit")
    mode_x.add_argument("--check", action="store_true",
                        help="Test LLM connectivity and exit")
    mode_x.add_argument("--serve", action="store_true",
                        help="Start MCP server in SSE mode for network access")

    # ── LLM selection ──
    llm_group = parser.add_argument_group("LLM Configuration")
    llm_group.add_argument("--llm",
        choices=["gemini", "openai", "claude", "ollama"],
        default="gemini",
        metavar="PROVIDER",
        help="LLM provider: gemini | openai | claude | ollama  (default: gemini)",
    )
    llm_group.add_argument("--model", default=None,
        help="Override model name (e.g. llama3.1, gpt-4o, gemini-1.5-pro)")
    llm_group.add_argument("--ollama-url",
        default=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        metavar="URL",
        help="Ollama server URL (default: http://localhost:11434)",
    )

    # ── Agent options ──
    agent_group = parser.add_argument_group("Agent Options")
    agent_group.add_argument("--directory", "-d", default=None,
        help="Directory to organize (default: ./test_dump)")
    agent_group.add_argument("--query", "-q", default=None,
        help="Task for the agent")
    agent_group.add_argument("--verbose", "-v", action="store_true",
        help="Show step-by-step agent reasoning")

    # ── Setup options ──
    setup_group = parser.add_argument_group("Setup Options")
    setup_group.add_argument("--reset", action="store_true",
        help="With --setup: wipe and recreate test_dump/")

    # ── Transport options ──
    transport_group = parser.add_argument_group("MCP Transport Options")
    transport_group.add_argument("--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="MCP transport: stdio (local) or sse (network)  (default: stdio)",
    )
    transport_group.add_argument("--sse-host", default="0.0.0.0",
        help="SSE server host (default: 0.0.0.0)")
    transport_group.add_argument("--sse-port", type=int, default=8000,
        help="SSE server port (default: 8000)")

    return parser


def main():
    _print_banner()
    parser = _build_parser()
    args   = parser.parse_args()

    if args.check:
        cmd_check(args)
    elif args.setup:
        cmd_setup(args)
    elif args.serve:
        cmd_serve(args)
    else:
        cmd_run(args)


if __name__ == "__main__":
    main()
