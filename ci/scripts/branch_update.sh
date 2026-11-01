#!/usr/bin/env bash
set -euo pipefail

REMOTE=${REMOTE:-origin}
MAIN_BRANCH=${MAIN_BRANCH:-main}
BASE_REF="$REMOTE/$MAIN_BRANCH"
dry_run=0

usage() {
  cat <<'EOF'
Usage: make branch-update [ARGS="--dry-run"]

Fetch the latest base branch and rebase the current development branch onto it.
This command never deletes or pushes a remote branch.

Options:
  --dry-run   Show the planned update without changing the branch.
  -h, --help  Show this help.

Environment:
  REMOTE       remote name (default: origin)
  MAIN_BRANCH  base branch name (default: main)
EOF
}

die() {
  echo "error: $*" >&2
  exit 1
}

for arg in "$@"; do
  case "$arg" in
    --dry-run) dry_run=1 ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; die "unknown argument: $arg" ;;
  esac
done

git rev-parse --is-inside-work-tree >/dev/null 2>&1 || die "not inside a git repository"
branch=$(git symbolic-ref --quiet --short HEAD) || die "HEAD is detached; check out a branch first"
default_branch=$(git symbolic-ref --quiet --short "refs/remotes/$REMOTE/HEAD" 2>/dev/null || true)
default_branch=${default_branch#"$REMOTE/"}
if [ "$branch" = "$MAIN_BRANCH" ] || { [ -n "$default_branch" ] && [ "$branch" = "$default_branch" ]; }; then
  die "branch-update only supports development branches; refusing to rebase $branch"
fi

[ -z "$(git status --porcelain)" ] || die "working tree has uncommitted changes; commit or stash them first"

echo "==> Fetching $REMOTE"
git fetch --prune "$REMOTE"
git show-ref --verify --quiet "refs/remotes/$BASE_REF" || die "missing $BASE_REF after fetch"

upstream=$(git rev-parse --abbrev-ref --symbolic-full-name '@{upstream}' 2>/dev/null || true)
if [ -n "$upstream" ] && ! git merge-base --is-ancestor "$upstream" HEAD; then
  die "$upstream contains commits not present locally; reconcile the remote branch first"
fi

if [ "$dry_run" -eq 1 ]; then
  echo "[dry-run] git rebase $BASE_REF"
  exit 0
fi

echo "==> Rebasing $branch onto $BASE_REF"
if ! git rebase "$BASE_REF"; then
  git rebase --abort >/dev/null 2>&1 || true
  die "rebase failed; it was aborted"
fi

echo "==> Rebase complete"
echo "  branch: $(git rev-parse --short HEAD)"
echo "  base:   $(git rev-parse --short "$BASE_REF")"
if [ -n "$upstream" ]; then
  echo "  next:   review the diff, then push with git push --force-with-lease"
fi
