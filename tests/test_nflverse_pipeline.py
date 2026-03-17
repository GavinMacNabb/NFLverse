from pathlib import Path
import tempfile
import unittest

from scripts import nflverse_pipeline as pipeline


class DatasetResolutionTests(unittest.TestCase):
    def test_single_asset_resolution_uses_verified_asset_name(self) -> None:
        config = pipeline.DatasetConfig(
            name="players",
            release_tag="players",
            mode="single",
            table_name="players",
            asset_name="players.parquet",
        )
        release = {
            "assets": [
                {"name": "players.csv"},
                {"name": "players.parquet", "browser_download_url": "https://example.test/players.parquet"},
            ]
        }

        selection = pipeline.resolve_single_asset(config, release, Path("data/raw/nfl"))

        self.assertEqual(selection.asset["name"], "players.parquet")
        self.assertEqual(selection.target_path, Path("data/raw/nfl/players/players.parquet"))

    def test_seasonal_asset_resolution_defaults_to_latest_available_season(self) -> None:
        config = pipeline.DatasetConfig(
            name="pbp",
            release_tag="pbp",
            mode="seasonal",
            table_name="pbp",
            asset_pattern="play_by_play_{season}.parquet",
        )
        release = {
            "assets": [
                {"name": "play_by_play_2024.parquet", "browser_download_url": "https://example.test/2024.parquet"},
                {"name": "play_by_play_2025.parquet", "browser_download_url": "https://example.test/2025.parquet"},
            ]
        }

        selections = pipeline.resolve_seasonal_assets(config, release, Path("data/raw/nfl"), None)

        self.assertEqual([selection.season for selection in selections], [2025])
        self.assertEqual(
            selections[0].target_path,
            Path("data/raw/nfl/pbp/season=2025/play_by_play_2025.parquet"),
        )

    def test_seasonal_asset_resolution_rejects_missing_seasons(self) -> None:
        config = pipeline.DatasetConfig(
            name="rosters",
            release_tag="rosters",
            mode="seasonal",
            table_name="rosters",
            asset_pattern="roster_{season}.parquet",
        )
        release = {
            "assets": [
                {"name": "roster_2025.parquet", "browser_download_url": "https://example.test/2025.parquet"},
            ]
        }

        with self.assertRaises(RuntimeError):
            pipeline.resolve_seasonal_assets(config, release, Path("data/raw/nfl"), [2024, 2025])


class DownloadMetadataTests(unittest.TestCase):
    def test_skip_download_requires_matching_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            destination = Path(temp_dir) / "players.parquet"
            metadata_path = destination.with_suffix(".parquet.metadata.json")
            destination.write_text("stub")
            metadata_path.write_text(
                """
                {
                  "source_asset_updated_at": "2026-03-14T08:29:10Z",
                  "source_digest": "sha256:test",
                  "source_size": 100
                }
                """
            )

            should_skip = pipeline.should_skip_download(
                metadata_path=metadata_path,
                asset={
                    "updated_at": "2026-03-14T08:29:10Z",
                    "digest": "sha256:test",
                    "size": 100,
                },
                destination=destination,
                force=False,
            )

            self.assertTrue(should_skip)


class SeasonRangeTests(unittest.TestCase):
    def test_normalize_season_bounds_accepts_valid_range(self) -> None:
        self.assertEqual(pipeline.normalize_season_bounds(2021, 2025), (2021, 2025))

    def test_normalize_season_bounds_rejects_reversed_range(self) -> None:
        with self.assertRaises(ValueError):
            pipeline.normalize_season_bounds(2025, 2021)


if __name__ == "__main__":
    unittest.main()
