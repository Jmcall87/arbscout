#!/bin/sh
# Run on a PC with git and the GitHub CLI installed and authenticated.
# Usage: sh scripts/setup-github.sh [repo-name] [--private|--public]
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$root"

if ! command -v git >/dev/null 2>&1; then
  echo "git is required" >&2
  exit 1
fi
if ! command -v gh >/dev/null 2>&1; then
  echo "GitHub CLI (gh) is required: https://cli.github.com" >&2
  exit 1
fi

repo=${1:-arbscout}
visibility=${2:---private}

if [ ! -d .git ]; then
  git init -b main
fi
git add .
git commit -m "ArbScout: shared PWA, APK shell and market research agent" || echo "Nothing new to commit"

gh repo create "$repo" "$visibility" --source=. --remote=origin --push

echo "Created and pushed $repo"
echo "Next: enable Pages (Settings -> Pages -> Source: GitHub Actions), then run the 'Release website + APK' workflow."
