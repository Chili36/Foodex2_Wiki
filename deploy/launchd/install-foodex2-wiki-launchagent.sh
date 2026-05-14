#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
TEMPLATE="${SCRIPT_DIR}/com.chili36.foodex2-wiki.plist"
DEST_DIR="${HOME}/Library/LaunchAgents"
DEST="${DEST_DIR}/com.chili36.foodex2-wiki.plist"
PYTHON_BIN="${FOODEX2_WIKI_PYTHON:-${REPO_ROOT}/.venv/bin/python}"

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "Expected executable Python at ${PYTHON_BIN}" >&2
  echo "Set FOODEX2_WIKI_PYTHON=/path/to/python to override." >&2
  exit 1
fi

escape_sed() {
  printf '%s' "$1" | sed 's/[\/&]/\\&/g'
}

mkdir -p "${DEST_DIR}"
sed \
  -e "s/__REPO_ROOT__/$(escape_sed "${REPO_ROOT}")/g" \
  -e "s/__PYTHON_BIN__/$(escape_sed "${PYTHON_BIN}")/g" \
  "${TEMPLATE}" > "${DEST}"

plutil -lint "${DEST}"

cat <<EOF
Installed ${DEST}

Reload with:
  launchctl bootout gui/\$(id -u) ${DEST} 2>/dev/null || true
  launchctl bootstrap gui/\$(id -u) ${DEST}
  launchctl kickstart -k gui/\$(id -u)/com.chili36.foodex2-wiki
EOF
