#!/usr/bin/env bash

set -euo pipefail

new_version="${1:?new version is required}"
version_file="${2:-VERSION}"
version_md_file="${3:-VERSION.md}"
package_json_file="${4:-package.json}"

printf '%s\n' "$new_version" > "$version_file"

awk -v version="$new_version" '
  /<!-- version:start -->/ {
    print
    getline
    print "`" version "`"
    next
  }
  { print }
' "$version_md_file" > "$version_md_file.tmp"
mv "$version_md_file.tmp" "$version_md_file"

if [[ -f "$package_json_file" ]]; then
  perl -0pi -e 's/"version":\s*"[^"]+"/"version": "'"$new_version"'"/' "$package_json_file"
fi
