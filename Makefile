.DEFAULT_GOAL := help
.PHONY: help opencode opencode-clear branch-update

PYTHON ?= python3
ARGS ?=

help:
	@printf '\nUsage: make <target> [ARGS="..."]\n\n'
	@printf '  %-18s %s\n' 'help' 'show available targets'
	@printf '  %-18s %s\n' 'opencode' 'start OpenCode with proxy variables disabled'
	@printf '  %-18s %s\n' 'opencode-clear' 'list and safely clear OpenCode sessions (ARGS: --all/--dry-run/--yes)'
	@printf '  %-18s %s\n' 'branch-update' 'rebase the current development branch onto origin/main (ARGS: --dry-run)'

opencode:
	@command -v opencode >/dev/null 2>&1 || { echo "error: opencode is not installed" >&2; exit 1; }
	@unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy ALL_PROXY all_proxy; \
		NO_PROXY="*" no_proxy="*" opencode

opencode-clear:
	@$(PYTHON) ci/scripts/opencode_clear.py $(ARGS)

branch-update:
	@bash ci/scripts/branch_update.sh $(ARGS)
