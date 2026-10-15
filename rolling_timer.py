#!/bin/env python
import pathlib
import tkinter as tk
import tomllib
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from itertools import chain

ROLLING_TIMER_DIR = pathlib.Path.home() / ".rolling_timer"
JSONL_FILE = ROLLING_TIMER_DIR / "time_intervals.jsonl"
CONFIG_FILE = ROLLING_TIMER_DIR / "config.toml"
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


def db_add_time_interval(db: sqlite3.Connection, time_interval: TimeInterval) -> None:
    db.execute(
        "INSERT INTO time_intervals (start_time, end_time) VALUES (?, ?)",
        (time_interval.start.isoformat(), time_interval.end.isoformat()),
    )
    db.commit()


def save_config(window: timedelta) -> None:
    CONFIG_FILE.write_text(
        f"sliding_window_hours={window.total_seconds() / 3600:g}\n", encoding="utf-8"
    )


def load_config() -> timedelta:
    if CONFIG_FILE.exists():
        with CONFIG_FILE.open("rb") as file:
            return timedelta(hours=tomllib.load(file)["sliding_window_hours"])
    return timedelta(hours=24)


def time_used(intervals: Iterable[TimeInterval], window: TimeInterval) -> timedelta:
    return sum((interval.overlap_duration(window) for interval in intervals), ZERO_TIME)


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


class TimerApp:
    def __init__(self, root: tk.Tk, db: sqlite3.Connection, window: timedelta):
        self.root = root
        self.db = db
        self.window = window
        self.started_at: datetime | None = None
        self.edit_job: str | None = None

        root.title("Rolling Timer")
        root.configure(bg=BG)
        root.resizable(False, False)
        tk.Label(
            root, text="Rolling Timer", bg=BG, fg=FG, font=("Arial", 13, "bold")
        ).pack(pady=(23, 17))
        self.time_label = tk.Label(
            root,
            text="00:00:00",
            bg=BG,
            fg=FG,
            font=("Arial", 34, "bold"),
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
            controls,
            text="Sliding window",
            bg=BG,
            fg=FG,
            font=("Arial", 10),
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
        tk.Label(
            controls,
            text="hours",
            bg=BG,
            fg=FG,
            font=("Arial", 10),
        ).pack(side="left", padx=(6, 0))

        self.window_var.trace_add("write", self.schedule_edit)
        self.window_entry.bind("<Return>", self.finish_edit)
        self.window_entry.bind("<FocusOut>", self.finish_edit)
        self.tick()

    def toggle(self) -> None:
        now = datetime.now(timezone.utc)
        if self.started_at is None:
            self.started_at = now
            color, label = RED, "Stop"
        else:
            db_add_time_interval(self.db, TimeInterval(self.started_at, now))
            self.started_at = None
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
        except (ValueError, OSError):
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
        now = datetime.now(timezone.utc)
        intervals = db_load_intervals(self.db)
        if self.started_at is not None:
            intervals = chain(intervals, (TimeInterval(self.started_at, now),))
        used = time_used(intervals, TimeInterval(now - self.window, now))
        self.time_label.configure(text=format_duration(used))

    def tick(self) -> None:
        self.update_display()
        self.root.after(1000, self.tick)


def main() -> None:
    ROLLING_TIMER_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(JSONL_FILE) as db:
        db_init(db)
        root = tk.Tk()
        TimerApp(root, db, load_config())
        root.mainloop()


if __name__ == "__main__":
    main()
