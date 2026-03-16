# Changelog

All notable project changes should be recorded here in reverse chronological order.

Add pull request notes under `## [Unreleased]`. The release workflow moves that section into a numbered release entry when the PR is merged to `main`.

## [Unreleased]

### Changed

- Switched the canonical version source to the plain `VERSION` file
- Replaced manual version edits in pull requests with automated version bumping, changelog finalization, tagging, and GitHub release creation based on PR release labels
- Replaced the manual version/changelog PR gate with changelog-plus-release-label enforcement

## [0.1.0] - 2026-03-16

### Added

- Initial repository scaffold
- Project `README.md`
- Repository agent policy in `agents.md`
- Versioning policy in `VERSION.md`
- GitHub pull request template and enforcement workflow for version/changelog updates
- Automated formatting configuration and pull request formatting checks
- Automated GitHub release and tag workflow
