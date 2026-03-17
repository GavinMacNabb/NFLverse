from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import duckdb

from webapp.app import create_app


def build_test_database(path: Path) -> None:
    connection = duckdb.connect(str(path))
    connection.execute("CREATE SCHEMA raw_nfl")
    connection.execute("CREATE SCHEMA stage_nfl")
    connection.execute("CREATE SCHEMA admin")

    connection.execute("CREATE TABLE raw_nfl.players (gsis_id VARCHAR, display_name VARCHAR)")
    connection.execute("INSERT INTO raw_nfl.players VALUES ('00-001', 'Test Player')")

    connection.execute(
        """
        CREATE TABLE stage_nfl.players (
            player_id VARCHAR,
            gsis_id VARCHAR,
            display_name VARCHAR,
            short_name VARCHAR,
            first_name VARCHAR,
            last_name VARCHAR,
            position VARCHAR,
            latest_team VARCHAR,
            rookie_season INTEGER,
            status VARCHAR
        )
        """
    )
    connection.execute(
        """
        INSERT INTO stage_nfl.players VALUES
            ('00-0033873', '00-0033873', 'Patrick Mahomes', 'P. Mahomes', 'Patrick', 'Mahomes', 'QB', 'KC', 2017, 'ACT'),
            ('00-0034857', '00-0034857', 'Josh Allen', 'J. Allen', 'Josh', 'Allen', 'QB', 'BUF', 2018, 'ACT')
        """
    )

    connection.execute(
        """
        CREATE TABLE stage_nfl.teams (
            team VARCHAR,
            team_name VARCHAR,
            team_full_name VARCHAR
        )
        """
    )
    connection.execute(
        """
        INSERT INTO stage_nfl.teams VALUES
            ('KC', 'Chiefs', 'Kansas City Chiefs'),
            ('BUF', 'Bills', 'Buffalo Bills'),
            ('BAL', 'Ravens', 'Baltimore Ravens'),
            ('CIN', 'Bengals', 'Cincinnati Bengals')
        """
    )

    connection.execute(
        """
        CREATE TABLE stage_nfl.games (
            game_id VARCHAR,
            season INTEGER,
            week INTEGER,
            game_date DATE,
            away_team VARCHAR,
            away_score INTEGER,
            home_team VARCHAR,
            home_score INTEGER,
            stadium VARCHAR,
            is_completed BOOLEAN
        )
        """
    )
    connection.execute(
        """
        INSERT INTO stage_nfl.games VALUES
            ('2021_01_BUF_KC', 2021, 1, '2021-09-12', 'BUF', 29, 'KC', 38, 'Arrowhead Stadium', TRUE),
            ('2021_01_BAL_CIN', 2021, 1, '2021-09-12', 'BAL', 24, 'CIN', 27, 'Paycor Stadium', TRUE),
            ('2021_02_KC_BAL', 2021, 2, '2021-09-19', 'KC', 35, 'BAL', 36, 'M&T Bank Stadium', TRUE)
        """
    )

    connection.execute(
        """
        CREATE TABLE stage_nfl.game_teams (
            game_id VARCHAR,
            season INTEGER,
            week INTEGER,
            game_date DATE,
            team VARCHAR,
            opponent_team VARCHAR,
            home_away VARCHAR,
            team_result VARCHAR,
            team_score INTEGER,
            opponent_score INTEGER,
            point_diff INTEGER
        )
        """
    )
    connection.execute(
        """
        INSERT INTO stage_nfl.game_teams VALUES
            ('2021_01_BUF_KC', 2021, 1, '2021-09-12', 'KC', 'BUF', 'home', 'W', 38, 29, 9),
            ('2021_01_BUF_KC', 2021, 1, '2021-09-12', 'BUF', 'KC', 'away', 'L', 29, 38, -9),
            ('2021_02_KC_BAL', 2021, 2, '2021-09-19', 'KC', 'BAL', 'away', 'L', 35, 36, -1),
            ('2021_02_KC_BAL', 2021, 2, '2021-09-19', 'BAL', 'KC', 'home', 'W', 36, 35, 1)
        """
    )

    connection.execute(
        "CREATE TABLE admin.stage_build_inventory (table_name VARCHAR, row_count BIGINT, start_season INTEGER, end_season INTEGER)"
    )
    connection.execute(
        """
        INSERT INTO admin.stage_build_inventory VALUES
            ('players', 2, 2021, 2025),
            ('teams', 4, 2021, 2025),
            ('games', 3, 2021, 2025),
            ('game_teams', 4, 2021, 2025)
        """
    )

    connection.execute(
        "CREATE TABLE admin.ingestion_inventory (dataset_name VARCHAR, table_name VARCHAR, file_count BIGINT, source_glob VARCHAR, built_at_utc VARCHAR)"
    )
    connection.execute(
        "INSERT INTO admin.ingestion_inventory VALUES ('players', 'players', 1, 'data/raw/nfl/players/*.parquet', '2026-01-01T00:00:00Z')"
    )

    connection.close()


class WebAppTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "test.duckdb"
        build_test_database(self.database_path)
        self.app = create_app({"TESTING": True, "DATABASE_PATH": str(self.database_path)})
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_index_lists_known_tables(self) -> None:
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("raw_nfl", body)
        self.assertIn("stage_nfl", body)
        self.assertIn("players", body)
        self.assertIn("games", body)

    def test_table_detail_renders_preview(self) -> None:
        response = self.client.get("/table/raw_nfl/players")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Test Player", body)
        self.assertIn("gsis_id", body)

    def test_schema_detail_renders_schema_tables(self) -> None:
        response = self.client.get("/schema/stage_nfl")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Stage Layer", body)
        self.assertIn("games", body)

    def test_player_search_renders_matches(self) -> None:
        response = self.client.get("/players?limit=1")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Josh Allen", body)
        self.assertIn("Next", body)

    def test_team_search_renders_paginated_schedule(self) -> None:
        response = self.client.get("/teams?season=2021&team=KC&limit=1")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("BUF", body)
        self.assertIn("Next", body)

    def test_week_search_renders_games(self) -> None:
        response = self.client.get("/weeks?season=2021&week=1&limit=10")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Arrowhead Stadium", body)
        self.assertIn("Paycor Stadium", body)

    def test_missing_table_returns_404(self) -> None:
        response = self.client.get("/table/raw_nfl/does_not_exist")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
