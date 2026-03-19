#!/usr/bin/env bash
set -euo pipefail

remote="${1:-origin}"

default_ref="$(git symbolic-ref --quiet --short "refs/remotes/${remote}/HEAD" 2>/dev/null || true)"
default_branch="${default_ref#${remote}/}"
if [[ -z "${default_branch}" || "${default_branch}" == "${default_ref}" ]]; then
  default_branch="main"
fi

echo "Fetching ${remote}/${default_branch}..."
git fetch --quiet "${remote}" "${default_branch}"

if ! git merge-base --is-ancestor "${remote}/${default_branch}" HEAD; then
  cat <<EOF
Branch is behind ${remote}/${default_branch}.
Rebase or merge latest ${default_branch} before pushing or opening a PR.
Suggested command:
  git fetch ${remote} && git rebase ${remote}/${default_branch}
EOF
  exit 1
fi

echo "Branch contains latest ${remote}/${default_branch}."
