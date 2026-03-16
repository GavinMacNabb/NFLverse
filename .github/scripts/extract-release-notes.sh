#!/usr/bin/env bash

set -euo pipefail

version="${1:?version is required}"
changelog_file="${2:-CHANGELOG.md}"

notes="$(
  awk -v version="$version" '
    $0 ~ "^## \\[" version "\\]" {
      capture = 1
      next
    }
    capture && $0 ~ "^## \\[" {
      exit
    }
    capture {
      print
    }
  ' "$changelog_file"
)"

if [[ -z "${notes//[$'\t\r\n ']/}" ]]; then
  echo "No changelog section found for version $version in $changelog_file" >&2
  exit 1
fi

printf '%s\n' "$notes"
