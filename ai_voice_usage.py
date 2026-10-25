#!/usr/bin/env python3
"""Manually monitor ChatGPT Voice usage over a sliding time window."""

import math
import os
import pathlib
import sqlite3
import sys
import tkinter as tk
import tomllib
from collections.abc import Callable, Iterable
from contextlib import closing
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

APP_NAME = "AI-VoiceUsage"


AI_VOICE_USAGE_DIR = (
    pathlib.Path(os.environ["LOCALAPPDATA"]) / APP_NAME
    if sys.platform == "win32"
    else pathlib.Path.home() / ".ai-voice-usage"
)
DATABASE_FILE = AI_VOICE_USAGE_DIR / "time_intervals.sqlite3"
CONFIG_FILE = AI_VOICE_USAGE_DIR / "config.toml"
ZERO_TIME = timedelta()

def utc_now() -> datetime:
    return datetime.now(UTC)
    
@dataclass(frozen=True)
class TimeInterval:
    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise ValueError("end_time must be >= start_time")

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
        TimeInterval(datetime.fromisoformat(start), datetime.fromisoformat(end))
        for start, end in db.execute("SELECT start_time, end_time FROM time_intervals")
    )


def db_start_session(db: sqlite3.Connection, now: datetime) -> int:
    cursor = db.execute(
        "INSERT INTO time_intervals (start_time, end_time) VALUES (?, ?)",
        (now.isoformat(), now.isoformat()),
    )
    db.commit()
    assert cursor.lastrowid is not None
    return cursor.lastrowid


def db_update_session(db: sqlite3.Connection, session_id: int, now: datetime) -> None:
    db.execute(
        "UPDATE time_intervals SET end_time = ? WHERE rowid = ?",
        (now.isoformat(), session_id),
    )
    db.commit()


def save_config(window: timedelta) -> None:
    CONFIG_FILE.write_text(
        f"sliding_window_hours = {window.total_seconds() / 3600:g}\n",
        encoding="utf-8",
    )


def load_config() -> timedelta:
    if CONFIG_FILE.exists():
        with CONFIG_FILE.open("rb") as file:
            return window_from_hours(float(tomllib.load(file)["sliding_window_hours"]))
    return timedelta(hours=24)


def time_used(intervals: Iterable[TimeInterval], window: TimeInterval) -> timedelta:
    return sum((interval.overlap_duration(window) for interval in intervals), ZERO_TIME)


def window_from_hours(hours: float) -> timedelta:
    if not math.isfinite(hours) or hours <= 0:
        raise ValueError("Sliding window must be a positive, finite number")
    return timedelta(hours=hours)
    
def format_duration(duration: timedelta) -> str:
    hours, remainder = divmod(int(duration.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"


BG = "#202620"
FG = "#f2f6f1"
GREEN = "#65df8b"
RED = "#eb8d83"
FIELD = "#303b32"
INVALID = "#573735"


class App:
    def __init__(
        self,
        root: tk.Tk,
        db: sqlite3.Connection,
        window: timedelta,
        clock: Callable[[], datetime] = utc_now,
    ):
        self.root = root
        self.db = db
        self.window = window
        self.clock = clock
        self.session_id: int | None = None
        self.edit_job: str | None = None

        root.title(APP_NAME)
        root.configure(bg=BG)
        root.resizable(False, False)
        tk.Label(
            root, text=APP_NAME, bg=BG, fg=FG, font=("Arial", 13, "bold")
        ).pack(pady=(23, 17))
        self.time_label = tk.Label(
            root, text="00:00:00", bg=BG, fg=FG, font=("Arial", 34, "bold")
        )
        self.time_label.pack(padx=34, pady=(0, 19))
        self.toggle_button = tk.Button(
            root,
            text="Start",
            command=self.toggle,
            width=13,
            bg=GREEN,
            fg=BG,
            activebackground=GREEN,
            activeforeground=BG,
            font=("Arial", 12, "bold"),
            pady=10,
            borderwidth=0,
        )
        self.toggle_button.pack(pady=(0, 25))
        controls = tk.Frame(root, bg=BG)
        controls.pack(padx=24, pady=(0, 24))
        tk.Label(
            controls, text="Sliding window", bg=BG, fg=FG, font=("Arial", 10)
        ).pack(side="left", padx=(0, 10))
        self.window_var = tk.StringVar(value=f"{window.total_seconds() / 3600:g}")
        self.window_entry = tk.Entry(
            controls,
            textvariable=self.window_var,
            width=6,
            justify="center",
            bg=FIELD,
            fg=FG,
            insertbackground=FG,
            relief="flat",
            font=("Arial", 11),
        )
        self.window_entry.pack(side="left")
        tk.Label(controls, text="hours", bg=BG, fg=FG, font=("Arial", 10)).pack(
            side="left", padx=(6, 0)
        )

        self.window_var.trace_add("write", self.schedule_edit)
        self.window_entry.bind("<Return>", self.finish_edit)
        self.window_entry.bind("<FocusOut>", self.finish_edit)
        root.protocol("WM_DELETE_WINDOW", self.close)
        self.tick()

    def toggle(self) -> None:
        now = self.clock()
        if self.session_id is None:
            self.session_id = db_start_session(self.db, now)
            color, label = RED, "Stop"
        else:
            db_update_session(self.db, self.session_id, now)
            self.session_id = None
            color, label = GREEN, "Start"
        self.toggle_button.configure(text=label, bg=color, activebackground=color)
        self.update_display()

    def schedule_edit(self, *_args: object) -> None:
        if self.edit_job is not None:
            self.root.after_cancel(self.edit_job)
        self.edit_job = self.root.after(350, self.apply_edit)

    def apply_edit(self) -> bool:
        self.edit_job = None
        try:
            window = window_from_hours(float(self.window_var.get()))
            if window != self.window:
                save_config(window)
        except (ValueError, OverflowError, OSError):
            self.window_entry.configure(bg=INVALID)
            return False
        self.window = window
        self.window_entry.configure(bg=FIELD)
        self.update_display()
        return True

    def finish_edit(self, _event: tk.Event) -> None:
        if self.edit_job is not None:
            self.root.after_cancel(self.edit_job)
            self.edit_job = None
        if not self.apply_edit():
            self.window_var.set(f"{self.window.total_seconds() / 3600:g}")
            if self.edit_job is not None:
                self.root.after_cancel(self.edit_job)
                self.edit_job = None
            self.window_entry.configure(bg=FIELD)

    def update_display(self) -> None:
        now = self.clock()
        if self.session_id is not None:
            db_update_session(self.db, self.session_id, now)
        used = time_used(
            db_load_intervals(self.db), TimeInterval(now - self.window, now)
        )
        self.time_label.configure(text=format_duration(used))

    def tick(self) -> None:
        self.update_display()
        self.root.after(1000, self.tick)

    def close(self) -> None:
        if self.session_id is not None:
            db_update_session(self.db, self.session_id, self.clock())
        self.root.destroy()


def main() -> None:
    AI_VOICE_USAGE_DIR.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(DATABASE_FILE)) as db:
        db_init(db)
        root = tk.Tk()
        App(root, db, load_config())
        root.mainloop()

if __name__ == "__main__":
    main()
