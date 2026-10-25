import pathlib
import runpy
import sqlite3
import unittest
from datetime import UTC, datetime, timedelta, timezone
from unittest.mock import patch

import ai_voice_usage as app
from usage_plot import forecast_points

NOW = datetime.now(UTC)
SECOND = timedelta(seconds=1)
HOUR = timedelta(hours=1)


class TimeIntervalTests(unittest.TestCase):
    def test_end_before_start_is_rejected(self):
        with self.assertRaises(ValueError):
            app.TimeInterval(NOW, NOW - HOUR)

    def test_zero_length_interval_is_valid(self):
        interval = app.TimeInterval(NOW, NOW)
        self.assertEqual(interval.overlap_duration(interval), timedelta())

    def test_partial_overlap(self):
        # offset (s) 10   15   20   25
        # first      [---------]
        # second          [---------]
        # overlap         [----]  5 s
        first = app.TimeInterval(NOW + 10 * SECOND, NOW + 20 * SECOND)
        second = app.TimeInterval(NOW + 15 * SECOND, NOW + 25 * SECOND)
        self.assertEqual(first.overlap_duration(second), 5 * SECOND)
        self.assertEqual(second.overlap_duration(first), 5 * SECOND)

    def test_contained_interval(self):
        # offset (s) 10  12          18  20
        # outer      [-------------------]
        # inner          [-----------]  entire inner interval: 6 s
        outer = app.TimeInterval(NOW + 10 * SECOND, NOW + 20 * SECOND)
        inner = app.TimeInterval(NOW + 12 * SECOND, NOW + 18 * SECOND)
        self.assertEqual(outer.overlap_duration(inner), 6 * SECOND)
        self.assertEqual(inner.overlap_duration(outer), 6 * SECOND)

    def test_identical_intervals(self):
        # offset (s) 10        20
        # first      [---------]
        # second     [---------]  full overlap: 10 s
        interval = app.TimeInterval(NOW + 10 * SECOND, NOW + 20 * SECOND)
        self.assertEqual(interval.overlap_duration(interval), 10 * SECOND)

    def test_separate_intervals(self):
        # offset (s) 0    5    10        20
        # before     [----]
        # after                [---------]  no overlap: 0 s
        before = app.TimeInterval(NOW, NOW + 5 * SECOND)
        after = app.TimeInterval(NOW + 10 * SECOND, NOW + 20 * SECOND)
        self.assertEqual(before.overlap_duration(after), timedelta())
        self.assertEqual(after.overlap_duration(before), timedelta())

    def test_touching_intervals(self):
        # offset (s) 10        20        30
        # first      [---------]
        # second               [---------]  only share an endpoint: 0 s
        first = app.TimeInterval(NOW + 10 * SECOND, NOW + 20 * SECOND)
        second = app.TimeInterval(NOW + 20 * SECOND, NOW + 30 * SECOND)
        self.assertEqual(first.overlap_duration(second), timedelta())
        self.assertEqual(second.overlap_duration(first), timedelta())

    def test_overlap_compares_instants_across_timezones(self):
        # Same instants on the UTC timeline, expressed in different timezones:
        # first     [----------------]  NOW -> NOW + 1 h
        # second    [----------------]  UTC-03 representation: same 1 h
        local = NOW.astimezone(timezone(timedelta(hours=-3)))
        first = app.TimeInterval(NOW, NOW + HOUR)
        second = app.TimeInterval(local, local + HOUR)
        self.assertEqual(first.overlap_duration(second), HOUR)

    def test_default_clock_uses_utc(self):
        self.assertEqual(app.utc_now().tzinfo, UTC)


class UsageTests(unittest.TestCase):
    def test_empty_usage(self):
        self.assertEqual(
            app.time_used([], app.TimeInterval(NOW - HOUR, NOW)), timedelta()
        )

    def test_usage_adds_session_durations(self):
        # offset (s) 0         10        20        30             45             60
        # window     [-----------------------------------------------------------]
        # sessions             [---------]         [--------------]  10 + 15 = 25 s
        sessions = [
            app.TimeInterval(NOW + 10 * SECOND, NOW + 20 * SECOND),
            app.TimeInterval(NOW + 30 * SECOND, NOW + 45 * SECOND),
        ]
        window = app.TimeInterval(NOW, NOW + 60 * SECOND)
        self.assertEqual(app.time_used(sessions, window), 25 * SECOND)

    def test_usage_counts_only_the_part_inside_the_window(self):
        # offset (s) 5    10   15        25   30   35
        # window          [-------------------]
        # sessions   [---------]         [---------]
        # counted         [----]         [----]  5 + 5 = 10 s
        sessions = [
            app.TimeInterval(NOW + 5 * SECOND, NOW + 15 * SECOND),
            app.TimeInterval(NOW + 25 * SECOND, NOW + 35 * SECOND),
        ]
        window = app.TimeInterval(NOW + 10 * SECOND, NOW + 30 * SECOND)
        self.assertEqual(app.time_used(sessions, window), 10 * SECOND)

    def test_usage_ignores_sessions_outside_the_window(self):
        # offset (s) 0    5    10                  30   35   40
        # window               [-------------------]
        # sessions   [----]                             [----]  both outside: 0 s
        sessions = [
            app.TimeInterval(NOW, NOW + 5 * SECOND),
            app.TimeInterval(NOW + 35 * SECOND, NOW + 40 * SECOND),
        ]
        window = app.TimeInterval(NOW + 10 * SECOND, NOW + 30 * SECOND)
        self.assertEqual(app.time_used(sessions, window), timedelta())

    def test_duration_format(self):
        for seconds, expected in [
            (0, "00:00:00"),
            (9, "00:00:09"),
            (60, "00:01:00"),
            (3661.9, "01:01:01"),
            (360000, "100:00:00"),
        ]:
            with self.subTest(seconds=seconds):
                self.assertEqual(
                    app.format_duration(timedelta(seconds=seconds)), expected
                )


class ForecastTests(unittest.TestCase):
    def test_empty_forecast_is_zero(self):
        points = forecast_points([], NOW, app.SLIDING_WINDOW)
        self.assertEqual(points, [
            (NOW, timedelta()),
            (NOW + app.SLIDING_WINDOW, timedelta()),
        ])

    def test_session_recovers_linearly(self):
        interval = app.TimeInterval(NOW - 3 * HOUR, NOW - 3 * HOUR + 15 * SECOND)
        values = dict(forecast_points([interval], NOW, app.SLIDING_WINDOW))
        start = NOW + 21 * HOUR
        end = start + 15 * SECOND
        self.assertEqual(values[NOW], 15 * SECOND)
        self.assertEqual(values[start], 15 * SECOND)
        self.assertEqual(values[end], timedelta())
        midway = start + 5 * SECOND
        self.assertEqual(
            app.time_used([interval],
                          app.TimeInterval(midway - app.SLIDING_WINDOW, midway)),
            10 * SECOND,
        )

    def test_active_session_is_capped_at_now(self):
        interval = app.TimeInterval(NOW - 5 * SECOND, NOW + 10 * SECOND)
        points = forecast_points([interval], NOW, app.SLIDING_WINDOW)
        self.assertEqual(points[0][1], 5 * SECOND)
        self.assertEqual(points[-1][1], timedelta())


class DataDirectoryTests(unittest.TestCase):
    def test_data_paths_share_application_directory(self):
        directory = app.AI_VOICE_USAGE_DIR
        self.assertEqual(app.DATABASE_FILE, directory / "time_intervals.sqlite3")

    def test_windows_uses_local_app_data(self):
        local = pathlib.Path("custom-local-app-data")
        with (
            patch.object(app.sys, "platform", "win32"),
            patch.dict(app.os.environ, {"LOCALAPPDATA": str(local)}),
            patch.object(app.pathlib.Path, "home") as home,
        ):
            module = runpy.run_path(app.__file__)
            self.assertEqual(module["AI_VOICE_USAGE_DIR"], local / "AI-VoiceUsage")
            home.assert_not_called()

    def test_other_platforms_use_home_directory(self):
        home = pathlib.Path("user-home")
        for platform in ("linux", "darwin"):
            with (
                self.subTest(platform=platform),
                patch.object(app.sys, "platform", platform),
                patch.object(app.pathlib.Path, "home", return_value=home),
            ):
                module = runpy.run_path(app.__file__)
                self.assertEqual(module["AI_VOICE_USAGE_DIR"], home / ".ai-voice-usage")


class SQLiteTestCase(unittest.TestCase):
    """Each test gets a fresh database; no database files are created."""

    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        app.db_init(self.db)

    def tearDown(self):
        self.db.close()


class DatabaseTests(SQLiteTestCase):
    def test_initialization_is_repeatable_and_database_starts_empty(self):
        app.db_init(self.db)
        self.assertEqual(list(app.db_load_intervals(self.db)), [])

    def test_start_update_and_round_trip(self):
        start = NOW + 0.125 * SECOND
        session = app.db_start_session(self.db, start)
        self.assertEqual(
            list(app.db_load_intervals(self.db)), [app.TimeInterval(start, start)]
        )
        # chloe eu não entend esse start / hour? que diabos é isso?
        app.db_update_session(self.db, session, start + HOUR)
        self.assertEqual(
            list(app.db_load_intervals(self.db)),
            [app.TimeInterval(start, start + HOUR)],
        )
        self.assertFalse(self.db.in_transaction)

    def test_fractional_seconds_are_stored_as_numbers(self):
        start, end = NOW, NOW + 0.125 * SECOND
        session = app.db_start_session(self.db, start)
        app.db_update_session(self.db, session, end)
        row = self.db.execute(
            "SELECT start_time, end_time, typeof(start_time), typeof(end_time) "
            "FROM time_intervals"
        ).fetchone()
        self.assertEqual(row, (start.isoformat(), end.isoformat(), "text", "text"))
        self.assertEqual(
            list(app.db_load_intervals(self.db)), [app.TimeInterval(start, end)]
        )

    def test_update_only_changes_selected_session(self):
        first = app.db_start_session(self.db, NOW)
        second = app.db_start_session(self.db, NOW + HOUR)
        self.assertNotEqual(first, second)
        app.db_update_session(self.db, first, NOW + HOUR)
        # Loading has no ordering contract: compare the persisted intervals as a set.
        self.assertCountEqual(
            app.db_load_intervals(self.db),
            [
                app.TimeInterval(NOW, NOW + HOUR),
                app.TimeInterval(NOW + HOUR, NOW + HOUR),
            ],
        )


if __name__ == "__main__":
    unittest.main()
