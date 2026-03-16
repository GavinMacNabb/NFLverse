#!/usr/bin/env bash

set -euo pipefail

version="${1:?version is required}"
release_date="${2:?release date is required}"
changelog_file="${3:-CHANGELOG.md}"

tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT

prefix_file="$tmp_dir/prefix.txt"
notes_file="$tmp_dir/notes.txt"
suffix_file="$tmp_dir/suffix.txt"

awk -v prefix="$prefix_file" -v notes="$notes_file" -v suffix="$suffix_file" '
  BEGIN {
    state = "prefix"
  }
  {
    if (state == "prefix") {
      print $0 >> prefix
      if ($0 == "## [Unreleased]") {
        state = "notes"
      }
      next
    }

    if (state == "notes") {
      if ($0 ~ /^## \[/) {
        print $0 >> suffix
        state = "suffix"
      } else {
        print $0 >> notes
      }
      next
    }

    print $0 >> suffix
  }
' "$changelog_file"

if [[ ! -f "$notes_file" ]]; then
  echo "Could not locate the Unreleased section in $changelog_file" >&2
  exit 1
fi

clean_notes="$tmp_dir/clean-notes.txt"
sed '/^- No unreleased entries yet\.$/d' "$notes_file" > "$clean_notes"

trimmed_notes="$tmp_dir/trimmed-notes.txt"
awk '
  {
    lines[NR] = $0
    if ($0 !~ /^[[:space:]]*$/) {
      last_nonblank = NR
    }
  }
  END {
    started = 0
    for (i = 1; i <= last_nonblank; i++) {
      if (!started && lines[i] ~ /^[[:space:]]*$/) {
        continue
      }
      started = 1
      print lines[i]
    }
  }
' "$clean_notes" > "$trimmed_notes"

if [[ -z "$(tr -d '[:space:]' < "$trimmed_notes")" ]]; then
  echo "The Unreleased section in $changelog_file does not contain release notes." >&2
  exit 1
fi

{
  cat "$prefix_file"
  printf '\n- No unreleased entries yet.\n\n'
  printf '## [%s] - %s\n\n' "$version" "$release_date"
  cat "$trimmed_notes"
  printf '\n'
  if [[ -f "$suffix_file" ]]; then
    cat "$suffix_file"
  fi
} > "$changelog_file"
