#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
#  Cascade — Agentic Data Ingestion Pipeline
#  Quick-run script
# ═══════════════════════════════════════════════════════════════════
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python3"

# ── Colors ────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; DIM='\033[2m'; RESET='\033[0m'

banner() {
  echo -e "\n${CYAN}${BOLD}╔═══════════════════════════════════════════╗${RESET}"
  echo -e "${CYAN}${BOLD}║  $1${RESET}"
  echo -e "${CYAN}${BOLD}╚═══════════════════════════════════════════╝${RESET}\n"
}

usage() {
  echo -e "${BOLD}Cascade — Agentic Data Ingestion Pipeline${RESET}"
  echo
  echo -e "  ${BOLD}Usage:${RESET} $0 <command> [options]"
  echo
  echo -e "  ${BOLD}Commands:${RESET}"
  echo -e "    ${GREEN}setup${RESET}              Create venv and install all dependencies"
  echo -e "    ${GREEN}seed${RESET}               Populate test_dump/ with sample files"
  echo -e "    ${GREEN}demo${RESET}               Run agent on test_dump/ (Gemini, default)"
  echo -e "    ${GREEN}demo --llm ollama${RESET}  Run agent with local Ollama"
  echo -e "    ${GREEN}demo --llm openai${RESET}  Run agent with OpenAI"
  echo -e "    ${GREEN}demo --llm claude${RESET}  Run agent with Anthropic Claude"
  echo -e "    ${GREEN}run [dir] [query]${RESET}  Run agent on custom dir with custom query"
  echo -e "    ${GREEN}check${RESET}              Test LLM connectivity"
  echo -e "    ${GREEN}serve${RESET}              Start MCP server in SSE mode (port 8000)"
  echo -e "    ${GREEN}reset${RESET}              Wipe and reseed test_dump/"
  echo -e "    ${GREEN}help${RESET}               Show this message"
  echo
  echo -e "  ${DIM}Examples:${RESET}"
  echo -e "    ${DIM}./run.sh demo${RESET}"
  echo -e "    ${DIM}./run.sh demo --llm ollama${RESET}"
  echo -e "    ${DIM}./run.sh run ./my-data \"Find all invoices\"${RESET}"
  echo -e "    ${DIM}./run.sh check --llm openai${RESET}"
  echo
}

check_venv() {
  if [ ! -f "$VENV_PYTHON" ]; then
    echo -e "${RED}Virtual environment not found.${RESET}"
    echo -e "  Run: ${BOLD}./run.sh setup${RESET}"
    exit 1
  fi
}

check_env() {
  if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo -e "${YELLOW}⚠️  No .env file found.${RESET}"
    echo -e "  Run: cp .env.example .env  then fill in your API key"
    echo -e "  ${DIM}(Not needed if using --llm ollama)${RESET}"
    # Don't exit — Ollama users don't need a .env
  fi
}

# ── Commands ──────────────────────────────────────────────────────

cmd_setup() {
  banner "Setting Up Cascade"
  cd "$PROJECT_DIR"
  python3 -m venv .venv
  "$VENV_PYTHON" -m pip install -q --upgrade pip
  "$VENV_PYTHON" -m pip install -r requirements.txt
  echo -e "${GREEN}✅ Setup complete!${RESET}"
  echo -e "\n  Next steps:"
  echo -e "    1. ${BOLD}cp .env.example .env${RESET}  and fill in your API key"
  echo -e "       ${DIM}(or use --llm ollama for fully local inference)${RESET}"
  echo -e "    2. ${BOLD}./run.sh demo${RESET}"
  echo
}

cmd_seed() {
  check_venv
  banner "Seeding test_dump/"
  cd "$PROJECT_DIR"
  "$VENV_PYTHON" setup_data.py "${@}"
}

cmd_demo() {
  check_venv; check_env
  banner "Cascade Demo"
  cd "$PROJECT_DIR"
  # Pass remaining flags (e.g. --llm ollama) through to cascade.py
  "$VENV_PYTHON" cascade.py --demo "${@}"
}

cmd_run() {
  check_venv; check_env
  DIR="${1:-./test_dump}"
  QUERY="${2:-Organize all files and extract a structured schema}"
  shift 2 2>/dev/null || true
  banner "Cascade Agent"
  cd "$PROJECT_DIR"
  "$VENV_PYTHON" cascade.py \
    --directory "$DIR" \
    --query "$QUERY" \
    --verbose \
    "${@}"
}

cmd_check() {
  check_venv
  cd "$PROJECT_DIR"
  "$VENV_PYTHON" cascade.py --check "${@}"
}

cmd_serve() {
  check_venv
  banner "Cascade MCP Server (SSE)"
  cd "$PROJECT_DIR"
  "$VENV_PYTHON" cascade.py --serve "${@}"
}

cmd_reset() {
  check_venv
  banner "Resetting test_dump/"
  cd "$PROJECT_DIR"
  "$VENV_PYTHON" setup_data.py --reset
  echo -e "${GREEN}✅ test_dump/ reset to fresh state${RESET}"
}

# ── Dispatch ──────────────────────────────────────────────────────

CMD="${1:-help}"
shift 2>/dev/null || true

case "$CMD" in
  setup)  cmd_setup  "$@" ;;
  seed)   cmd_seed   "$@" ;;
  demo)   cmd_demo   "$@" ;;
  run)    cmd_run    "$@" ;;
  check)  cmd_check  "$@" ;;
  serve)  cmd_serve  "$@" ;;
  reset)  cmd_reset  "$@" ;;
  help|*) usage ;;
esac
