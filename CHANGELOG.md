# Changelog

All notable project changes should be recorded here in reverse chronological order.

Add pull request notes under `## [Unreleased]`. The release workflow moves that section into a numbered release entry when the PR is merged to `main`.

## [Unreleased]

### Changed

- Switched the canonical version source to the plain `VERSION` file
- Replaced manual version edits in pull requests with automated version bumping, changelog finalization, tagging, and GitHub release creation based on PR release labels
- Replaced the manual version/changelog PR gate with changelog-plus-release-label enforcement

### Added

- Initial NFL ingestion scaffold around official `nflverse-data` release assets
- Repeatable sync and local DuckDB build workflow for NFL `players`, `schedules`, `rosters`, and `pbp`
- Repo data layout for `raw`, `staging`, and `curated` outputs plus pipeline documentation
- Raw NFL `teams` ingestion plus a first `stage_nfl` layer for the 2021-2025 seasons
- Stage build and validation workflow for `teams`, `players`, `games`, `game_teams`, and `roster_snapshots`
- Raw NFL `draft_picks` and `combine` ingestion plus staged rookie, draft, and combine tables for 2021-2025
- Simple Flask table browser for the local DuckDB warehouse

## [0.1.0] - 2026-03-16

### Added

- Initial repository scaffold
- Project `README.md`
- Repository agent policy in `agents.md`
- Versioning policy in `VERSION.md`
- GitHub pull request template and enforcement workflow for version/changelog updates
- Automated formatting configuration and pull request formatting checks
- Automated GitHub release and tag workflow
