#!/usr/bin/env bash

set -euo pipefail

version_file="${1:-VERSION}"

if [[ ! -f "$version_file" ]]; then
  echo "Version file not found: $version_file" >&2
  exit 1
fi

version="$(tr -d '[:space:]' < "$version_file")"

if ! [[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "Could not read a semantic version from $version_file" >&2
  exit 1
fi

echo "$version"
