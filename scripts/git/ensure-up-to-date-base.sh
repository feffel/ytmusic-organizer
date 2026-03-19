#!/usr/bin/env bash
set -euo pipefail

remote="${1:-}"
target_rev_arg="${2:-}"

resolve_remote() {
  local candidate=""
  local branch_name=""
  local upstream_ref=""
  local upstream_remote=""

  if [[ -n "${remote}" ]]; then
    echo "${remote}"
    return 0
  fi

  if [[ -n "${YTMO_BASE_REMOTE:-}" ]]; then
    echo "${YTMO_BASE_REMOTE}"
    return 0
  fi

  # In fork workflows, canonical base is usually "upstream".
  if git remote get-url upstream >/dev/null 2>&1; then
    echo "upstream"
    return 0
  fi

  branch_name="$(git branch --show-current)"
  if [[ -n "${branch_name}" ]]; then
    upstream_ref="$(git for-each-ref --format='%(upstream:short)' "refs/heads/${branch_name}" 2>/dev/null || true)"
    if [[ -n "${upstream_ref}" && "${upstream_ref}" == */* ]]; then
      upstream_remote="${upstream_ref%%/*}"
      if [[ -n "${upstream_remote}" ]]; then
        echo "${upstream_remote}"
        return 0
      fi
    fi
  fi

  if [[ -n "${PRE_COMMIT_REMOTE_NAME:-}" ]]; then
    echo "${PRE_COMMIT_REMOTE_NAME}"
    return 0
  fi

  if git remote get-url origin >/dev/null 2>&1; then
    echo "origin"
    return 0
  fi

  candidate="$(git remote | head -n 1 || true)"
  if [[ -n "${candidate}" ]]; then
    echo "${candidate}"
    return 0
  fi

  return 1
}

resolve_target_rev() {
  local candidate=""

  if [[ -n "${target_rev_arg}" ]]; then
    if git rev-parse --verify --quiet "${target_rev_arg}^{commit}" >/dev/null; then
      echo "${target_rev_arg}"
      return 0
    fi
    echo "Unable to resolve target revision '${target_rev_arg}'." >&2
    return 1
  fi

  if [[ -n "${PRE_COMMIT_TO_REF:-}" ]]; then
    if git rev-parse --verify --quiet "${PRE_COMMIT_TO_REF}^{commit}" >/dev/null; then
      echo "${PRE_COMMIT_TO_REF}"
      return 0
    fi
    echo "Unable to resolve PRE_COMMIT_TO_REF='${PRE_COMMIT_TO_REF}' to a local commit." >&2
    return 1
  fi

  echo "HEAD"
}

if ! remote="$(resolve_remote)"; then
  remotes="$(git remote | tr '\n' ' ' | sed 's/[[:space:]]*$//')"
  cat <<EOF
Unable to resolve git remote for base freshness check.
Provide one explicitly:
  ./scripts/git/ensure-up-to-date-base.sh <remote> [target-rev]
Available remotes: ${remotes:-<none>}
EOF
  exit 1
fi

target_rev="$(resolve_target_rev)"


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

if ! git merge-base --is-ancestor "${remote}/${default_branch}" "${target_rev}"; then
  cat <<EOF
Revision '${target_rev}' is behind ${remote}/${default_branch}.
Rebase or merge latest ${default_branch} before pushing or opening a PR.
Suggested command:
  git fetch ${remote} && git rebase ${remote}/${default_branch}
EOF
  exit 1
fi

echo "Revision '${target_rev}' contains latest ${remote}/${default_branch}."
