#!/usr/bin/env bash

set -euo pipefail

event_name="${GITHUB_EVENT_NAME:-}"
pr_labels="${PR_LABELS:-}"

if [[ "$event_name" == "pull_request" ]]; then
  base_sha="${PR_BASE_SHA:?PR_BASE_SHA is required for pull_request events}"
  head_sha="${PR_HEAD_SHA:?PR_HEAD_SHA is required for pull_request events}"
else
  base_sha="$(git rev-parse HEAD^1)"
  head_sha="${GITHUB_SHA:-HEAD}"
fi

changed_files=()
while IFS= read -r file; do
  changed_files+=("$file")
done < <(git diff --name-only "$base_sha" "$head_sha")

if [[ "${#changed_files[@]}" -eq 0 ]]; then
  echo "No changed files detected."
  exit 0
fi

requires_release_metadata=0
changelog_touched=0

for file in "${changed_files[@]}"; do
  [[ -z "$file" ]] && continue

  case "$file" in
    CHANGELOG.md)
      changelog_touched=1
      ;;
  esac

  case "$file" in
    VERSION | VERSION.md | CHANGELOG.md | README.md | agents.md | .editorconfig | .gitignore | .prettierignore | .prettierrc.json | package.json | package-lock.json | .github/* | .github/** | docs/* | docs/**) ;;
    *)
      requires_release_metadata=1
      ;;
  esac
done

echo "Changed files:"
printf ' - %s\n' "${changed_files[@]}"

if [[ "$requires_release_metadata" -eq 0 ]]; then
  echo "Only administrative or documentation files changed. Changelog and release labels are not required."
  exit 0
fi

if [[ "$changelog_touched" -eq 0 ]]; then
  echo
  echo "This pull request changes project files but does not update CHANGELOG.md."
  exit 1
fi

if [[ "$event_name" != "pull_request" ]]; then
  echo "Merge-group event: changelog requirement satisfied. Release labels are validated in pull requests."
  exit 0
fi

matched_labels=()

for label in release:major release:minor release:patch; do
  case ",$pr_labels," in
    *,"$label",*)
      matched_labels+=("$label")
      ;;
  esac
done

if [[ "${#matched_labels[@]}" -ne 1 ]]; then
  echo
  echo "Exactly one release label is required for substantive pull requests."
  echo "Allowed labels: release:major, release:minor, release:patch"
  echo "Current labels: ${pr_labels:-<none>}"
  exit 1
fi

echo "Changelog and release label requirements satisfied."
