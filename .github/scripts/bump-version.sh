#!/usr/bin/env bash

set -euo pipefail

current_version="${1:?current version is required}"
bump_type="${2:?bump type is required}"

if ! [[ "$current_version" =~ ^([0-9]+)\.([0-9]+)\.([0-9]+)$ ]]; then
  echo "Invalid semantic version: $current_version" >&2
  exit 1
fi

major="${BASH_REMATCH[1]}"
minor="${BASH_REMATCH[2]}"
patch="${BASH_REMATCH[3]}"

case "$bump_type" in
  major)
    major=$((major + 1))
    minor=0
    patch=0
    ;;
  minor)
    minor=$((minor + 1))
    patch=0
    ;;
  patch)
    patch=$((patch + 1))
    ;;
  none) ;;
  *)
    echo "Unsupported bump type: $bump_type" >&2
    exit 1
    ;;
esac

printf '%s.%s.%s\n' "$major" "$minor" "$patch"
