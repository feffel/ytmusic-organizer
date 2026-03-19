#!/usr/bin/env bash
set -euo pipefail

remote="${1:-}"

if [[ -z "${remote}" && -n "${PRE_COMMIT_REMOTE_NAME:-}" ]]; then
  remote="${PRE_COMMIT_REMOTE_NAME}"
fi

if [[ -z "${remote}" ]]; then
  upstream_ref="$(git rev-parse --abbrev-ref --symbolic-full-name '@{upstream}' 2>/dev/null || true)"
  if [[ -n "${upstream_ref}" && "${upstream_ref}" == */* ]]; then
    remote="${upstream_ref%%/*}"
  fi
fi

if [[ -z "${remote}" ]]; then
  remote="origin"
fi

if ! git remote get-url "${remote}" >/dev/null 2>&1; then
  remotes="$(git remote | tr '\n' ' ' | sed 's/[[:space:]]*$//')"
  cat <<EOF
Unable to resolve git remote '${remote}'.
Provide a remote explicitly:
  ./scripts/git/ensure-up-to-date-base.sh <remote>
Or set branch upstream first:
  git branch --set-upstream-to <remote>/<branch>
Available remotes: ${remotes:-<none>}
EOF
  exit 1
fi

default_ref="$(git symbolic-ref --quiet --short "refs/remotes/${remote}/HEAD" 2>/dev/null || true)"
default_branch="${default_ref#${remote}/}"
if [[ -z "${default_branch}" || "${default_branch}" == "${default_ref}" ]]; then
  default_branch="$(
    git ls-remote --symref "${remote}" HEAD 2>/dev/null \
      | awk '/^ref:/ { sub("refs\/heads\/", "", $2); print $2; exit }'
  )"
fi
if [[ -z "${default_branch}" ]]; then
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
