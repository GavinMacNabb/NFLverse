# NFLverse

NFLverse is the home for our NFL and college football data work.

## What This Repo Is For

The goal is simple:

- Game schedules and results
- Team and conference data
- Rosters and player info
- Play-by-play and drive-level data
- Team and player stats
- Rankings, standings, and advanced metrics
- Historical data and season summaries

## How We Work

- Keep the data traceable back to a source.
- Keep workflows repeatable.
- Treat NFL and CFB as related but separate products.
- Keep the repo easy to grow.

## Versioning

Version notes live in `CHANGELOG.md`.

The actual version number lives in `VERSION`.

Normal flow:

- add notes under `## [Unreleased]` in `CHANGELOG.md`
- add one PR label: `release:major`, `release:minor`, `release:patch`, or `release:none`
- let GitHub handle the version bump, tag, and release after merge

## Formatting

Formatting is checked in pull requests.

Use:

- `npm install`
- `npm run format`
- `npm run format:check`

## Planned Layout

As the repo grows, it will probably look something like this:

```text
data/
  raw/
  staging/
  curated/
notebooks/
src/
tests/
docs/
```

## Status

This is still an early scaffold. The structure is in place, but the actual data pipelines and analytics work are still ahead.
