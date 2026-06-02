#!/usr/bin/env bash
# Bump zero-version tag (v0.major.minor), create it locally, and push to origin.
set -euo pipefail

BUMP_TYPE="${1:-}"

if [[ "$BUMP_TYPE" != "major" && "$BUMP_TYPE" != "minor" ]]; then
  echo "Usage: $0 <major|minor>" >&2
  exit 1
fi

if ! git rev-parse --git-dir >/dev/null 2>&1; then
  echo "Error: not a git repository." >&2
  exit 1
fi

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

echo "Fetching tags from origin..."
git fetch origin --tags --force

latest="$(git tag -l 'v0.*' | sort -V | tail -n 1 || true)"

if [[ -z "$latest" ]]; then
  echo "No existing v0.* tags found; starting at v0.1.0"
  new_tag="v0.1.0"
else
  echo "Latest tag: $latest"

  version="${latest#v}"
  if [[ ! "$version" =~ ^0\.[0-9]+\.[0-9]+$ ]]; then
    echo "Error: latest tag '$latest' is not in v0.major.minor format." >&2
    exit 1
  fi

  major_num="$(echo "$version" | cut -d. -f2)"
  minor_num="$(echo "$version" | cut -d. -f3)"

  if [[ "$BUMP_TYPE" == "major" ]]; then
    major_num=$((major_num + 1))
    minor_num=0
  else
    minor_num=$((minor_num + 1))
  fi

  new_tag="v0.${major_num}.${minor_num}"
fi

if git rev-parse "$new_tag" >/dev/null 2>&1; then
  echo "Error: tag '$new_tag' already exists." >&2
  exit 1
fi

current_branch="$(git branch --show-current)"
echo ""
echo "  Bump type:  $BUMP_TYPE"
echo "  Branch:     $current_branch"
echo "  New tag:    $new_tag"
echo ""

read -r -p "Create and push tag $new_tag to origin? [y/N] " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
  echo "Aborted."
  exit 0
fi

git tag -a "$new_tag" -m "Release $new_tag"
git push origin "$new_tag"

echo ""
echo "Done. Pushed $new_tag to origin."
echo "CI will publish the Docker image when the tag push completes."
