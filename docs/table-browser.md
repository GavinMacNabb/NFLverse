# Table Browser

The Flask app is a lightweight read-only browser for the local DuckDB file.

## What It Shows

- `raw_nfl`
- `stage_nfl`
- `admin`

For each table, the app shows:

- schema and table name
- staged row counts when available
- raw file counts when available
- column metadata
- paginated row previews

It also includes basic search pages for:

- player lookup from `stage_nfl.players`
- team schedule browsing from `stage_nfl.game_teams`
- week-by-week game browsing from `stage_nfl.games`

## Run It

Make sure the local database exists first:

```bash
make build-db
make build-stage
```

Then start the Flask app:

```bash
make run-app
```

Open:

<http://127.0.0.1:5000>

Search routes:

- <http://127.0.0.1:5000/players>
- <http://127.0.0.1:5000/teams>
- <http://127.0.0.1:5000/weeks>

## Notes

- The app opens DuckDB in read-only mode.
- It is intentionally not a general SQL runner.
- Preview pages support `limit` and `offset` query params, for example:
  `http://127.0.0.1:5000/table/stage_nfl/rookies?limit=25&offset=50`
- Search pages also use `limit` and `offset`, preserving the current filters in pagination links.
