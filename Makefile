.DEFAULT_GOAL := help
.PHONY: help cli opencode opencode-clear branch-update

PYTHON ?= python3
ARGS ?=
CLI_VENV ?= .venv
CLI_BIN := $(CLI_VENV)/bin

help:
	@printf '\nUsage: make <target> [ARGS="..."]\n\n'
	@printf '  %-18s %s\n' 'help' 'show available local development targets'
	@printf '  %-18s %s\n' 'cli' 'enter the mk business CLI shell (ARGS: one-shot command)'
	@printf '  %-18s %s\n' 'opencode' 'start OpenCode with proxy variables disabled'
	@printf '  %-18s %s\n' 'opencode-clear' 'list and safely clear OpenCode sessions (ARGS: --all/--dry-run/--yes)'
	@printf '  %-18s %s\n' 'branch-update' 'rebase the current development branch onto origin/main (ARGS: --dry-run)'
	@printf '\nInside the CLI shell run: mk --help\n\n'

cli:
	@if [ ! -x "$(CLI_BIN)/python" ] || ! "$(CLI_BIN)/python" -c 'import setuptools, click, jsonschema' >/dev/null 2>&1; then \
		printf 'Preparing %s with system Python packages...\n' "$(CLI_VENV)"; \
		rm -rf "$(CLI_VENV)"; \
		$(PYTHON) -m venv --system-site-packages "$(CLI_VENV)"; \
	fi
	@if ! "$(CLI_BIN)/python" -c 'import setuptools, click, jsonschema' >/dev/null 2>&1; then \
		printf 'error: setuptools, click and jsonschema are required in %s; install them first\n' "$(PYTHON)" >&2; \
		exit 1; \
	fi
	@$(CLI_BIN)/python -m pip install --quiet --disable-pip-version-check --no-index --no-build-isolation --no-deps -e .
	@if [ -n "$(ARGS)" ]; then \
		exec "$(CLI_BIN)/mk" $(ARGS); \
	else \
		printf 'mk CLI ready. Run "mk --help"; type "exit" to leave.\n'; \
		exec env PATH="$(CURDIR)/$(CLI_BIN):$$PATH" PS1="(mk) $$PS1" bash --norc --noprofile -i; \
	fi

opencode:
	@command -v opencode >/dev/null 2>&1 || { echo "error: opencode is not installed" >&2; exit 1; }
	@unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy ALL_PROXY all_proxy; \
		NO_PROXY="*" no_proxy="*" opencode

opencode-clear:
	@$(PYTHON) ci/scripts/opencode_clear.py $(ARGS)

branch-update:
	@bash ci/scripts/branch_update.sh $(ARGS)
