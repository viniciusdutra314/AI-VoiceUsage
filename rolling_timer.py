#!/bin/env python
import pathlib
import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta
from time import time

DATABASE_DIR = pathlib.Path.home() / ".rolling_timer"
DATABASE_DIR.mkdir(exist_ok=True)
DATABASE_FILE = DATABASE_DIR / "rolling_timer.sqlite3"
ZERO_TIME = timedelta()


@dataclass(frozen=True)
class TimeInterval:
    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise ValueError("end_time must be >= start_time")

    def duration(self) -> timedelta:
        return self.end - self.start

    def overlap_duration(self, other: "TimeInterval") -> timedelta:
        return max(
            ZERO_TIME,
            min(self.end, other.end) - max(self.start, other.start),
        )


def db_init(db: sqlite3.Connection) -> None:
    db.execute("""
        CREATE TABLE IF NOT EXISTS time_intervals (
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL
        )
    """)


def db_load_intervals(db: sqlite3.Connection) -> Iterable[TimeInterval]:
    return (
        TimeInterval(
            datetime.fromisoformat(start),
            datetime.fromisoformat(end),
        )
        for start, end in db.execute("SELECT start_time, end_time FROM time_intervals")
    )


def add_session(db: sqlite3.Connection, time_interval: TimeInterval) -> None:
    db.execute(
        "INSERT INTO time_intervals (start_time, end_time) VALUES (?, ?)",
        (time_interval.start.isoformat(), time_interval.end.isoformat()),
    )
    db.commit()


def time_left(
    intervals: Iterable[TimeInterval],
    sliding_window: TimeInterval,
    maximum_time: timedelta,
) -> timedelta:
    used = sum(
        (interval.overlap_duration(sliding_window) for interval in intervals),
        ZERO_TIME,
    )
    return max(ZERO_TIME, maximum_time - used)


def main() -> None:
    con = sqlite3.connect(DATABASE_FILE)
    db_init(con)


if __name__ == "__main__":
    main()
