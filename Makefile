PYTHON ?= python3
VENV ?= .venv
VENV_BIN := $(VENV)/bin
VENV_PYTHON := $(VENV_BIN)/python
DEV_LAUNCHER := $(VENV_BIN)/ai-governance-dev
POLICY := src/ai_governance_harness/governance/policies/default.yaml
EVIDENCE := src/ai_governance_harness/governance/agt-runtime-evidence.yaml
MCP_PORT ?= $(or $(shell sed -n 's/^MCP_PORT=//p' .env 2>/dev/null | tail -n 1),8001)
CHAT_PORT ?= $(or $(shell sed -n 's/^CHAT_PORT=//p' .env 2>/dev/null | tail -n 1),8080)

.DEFAULT_GOAL := help

.PHONY: help install run stop mcp chat test lint governance build audit check

help:
	@printf '%s\n' \
		'Usage: make <target>' \
		'' \
		'  install     Install the project and development dependencies' \
		'  run         Start the MCP server and chat UI together' \
		'  stop        Stop processes listening on the MCP and chat ports' \
		'  mcp         Start only the MCP server' \
		'  chat        Start only the chat UI' \
		'  test        Run the test suite' \
		'  lint        Run Ruff' \
		'  governance  Validate the governance toolkit, policy, and evidence' \
		'  build       Build the Python package' \
		'  audit       Audit installed dependencies' \
		'  check       Run lint, tests, governance validation, and build'

install: $(DEV_LAUNCHER)

$(DEV_LAUNCHER): pyproject.toml
	test -x $(VENV_PYTHON) || $(PYTHON) -m venv $(VENV)
	$(VENV_PYTHON) -m pip install -e ".[dev]"

run: $(DEV_LAUNCHER)
	$(DEV_LAUNCHER)

stop:
	@for port in $(MCP_PORT) $(CHAT_PORT); do \
		pids="$$(lsof -tiTCP:$$port -sTCP:LISTEN 2>/dev/null || true)"; \
		if test -n "$$pids"; then \
			echo "Stopping process(es) listening on port $$port: $$pids"; \
			kill $$pids; \
		else \
			echo "No process is listening on port $$port."; \
		fi; \
	done

mcp: $(DEV_LAUNCHER)
	$(VENV_BIN)/ai-governance-mcp

chat: $(DEV_LAUNCHER)
	$(VENV_BIN)/ai-governance-chat

test: $(DEV_LAUNCHER)
	$(VENV_PYTHON) -m pytest

lint: $(DEV_LAUNCHER)
	$(VENV_PYTHON) -m ruff check .

governance: $(DEV_LAUNCHER)
	PYTHONUTF8=1 $(VENV_BIN)/agt --json doctor
	PYTHONUTF8=1 $(VENV_BIN)/agt --json lint-policy --strict $(POLICY)
	PYTHONUTF8=1 $(VENV_BIN)/agt --json verify --evidence $(EVIDENCE)

build: $(DEV_LAUNCHER)
	$(VENV_PYTHON) -m build

audit: $(DEV_LAUNCHER)
	$(VENV_BIN)/ai-governance-audit

check: lint test governance build
