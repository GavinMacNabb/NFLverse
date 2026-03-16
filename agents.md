# Agent Rules For `football_db`

These rules apply to any agent making changes in this repository.

## Mission

Support a football data analytics platform centered on U.S. football datasets, with primary focus on:

- NFL
- College football (CFB)

All work should improve the repository's reliability, clarity, and long-term maintainability as a data product.

## Core Working Rules

1. Preserve data integrity.
   - Never fabricate values, sources, schemas, metrics, or record counts.
   - If a source or requirement is unclear, mark the gap explicitly instead of guessing.

2. Keep source provenance visible.
   - Every dataset, transformation, and derived metric should be traceable to an upstream source or documented business rule.
   - When adding new data assets or pipelines, include source notes in code or documentation.

3. Treat NFL and CFB as separate domains unless explicitly unified.
   - Do not assume the same identifiers, rules, schedule structures, postseason formats, or conference models apply across both.
   - Name league-specific logic clearly.

4. Prefer reproducible workflows.
   - Favor scripted ingestion and transformation over manual editing.
   - Keep inputs, outputs, and assumptions explicit.

5. Make safe changes.
   - Do not delete or overwrite user data, raw inputs, or existing outputs without a clear reason documented in the change.
   - Avoid destructive commands unless explicitly requested.

6. Keep documentation current.
   - Update `README.md` or related docs when behavior, structure, or workflows change.
   - Document new directories, pipelines, and conventions close to where they are introduced.

7. Optimize for auditability.
   - Use clear names for fields, files, and transformations.
   - Prefer small, reviewable changes over broad rewrites.

8. Validate before finishing.
   - Run relevant checks when code or data-processing logic changes.
   - If validation cannot be run, state that clearly.

## Data Standards

- Prefer stable identifiers where available.
- Preserve raw source data before applying cleaning logic.
- Separate raw, intermediate, and curated outputs.
- Record timezone, season, week, and league assumptions explicitly when relevant.
- Be careful with historical data where team names, conferences, or rules may have changed over time.

## Coding And Analysis Expectations

- Keep business logic out of notebooks when it should live in reusable code.
- Write transformations so they can be rerun consistently.
- Add concise comments only where logic is not obvious.
- Avoid hidden dependencies and undocumented local-only steps.

## Change Management

- If the repository is empty or early-stage, prefer lightweight scaffolding over premature complexity.
- If you introduce a new tool, framework, or storage convention, explain why.
- Do not reorganize the repo structure aggressively unless the benefit is clear and documented.

## When In Doubt

- Choose clarity over cleverness.
- Choose correctness over speed.
- Choose explicit documentation over implicit assumptions.
