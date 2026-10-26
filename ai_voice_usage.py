#!/usr/bin/env python3
"""Manually monitor ChatGPT Voice usage over a sliding time window."""

import os
import pathlib
import sqlite3
import sys
import tkinter as tk
from collections.abc import Callable, Iterable
from contextlib import closing
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

APP_NAME = "AI-VoiceUsage"
SLIDING_WINDOW = timedelta(hours=24)


AI_VOICE_USAGE_DIR = (
    pathlib.Path(os.environ["LOCALAPPDATA"]) / APP_NAME
    if sys.platform == "win32"
    else pathlib.Path.home() / ".ai-voice-usage"
)
DATABASE_FILE = AI_VOICE_USAGE_DIR / "time_intervals.sqlite3"
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


def time_used(intervals: Iterable[TimeInterval], window: TimeInterval) -> timedelta:
    return sum((interval.overlap_duration(window) for interval in intervals), ZERO_TIME)


def format_duration(duration: timedelta) -> str:
    hours, remainder = divmod(int(duration.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"


THEMES = {
    "dark": dict(bg="#0d1726", fg="#eaf2ff", hover="#1c304a",
                 accent="#2563eb", stop="#b83d55"),
    "light": dict(bg="#edf5ff", fg="#152a45", hover="#dbeafe",
                  accent="#1d4ed8", stop="#be123c"),
}


class App:
    def __init__(
        self,
        root: tk.Tk,
        db: sqlite3.Connection,
        clock: Callable[[], datetime] = utc_now,
    ):
        self.root = root
        self.db = db
        self.clock = clock
        self.session_id: int | None = None
        self.dark_mode = True

        root.title(APP_NAME)
        if root.tk.call("tk", "windowingsystem") == "x11":
            root.wm_attributes("-type", "utility")
        root.geometry("300x300")
        root.minsize(300, 300)
        root.resizable(True, True)
        self.title_label = tk.Label(root, text=APP_NAME, font=("Arial", -17, "bold"))
        self.title_label.place(x=16, y=28, anchor="w")
        self.time_label = tk.Label(
            root,
            text="00:00:00",
            font=("Arial", -60, "bold"),
            anchor="center",
            borderwidth=0,
            highlightthickness=0,
            padx=0,
            pady=0,
        )
        self.time_label.place(
            relx=0.5, rely=0.5, anchor="center", relwidth=0.92, relheight=0.42
        )
        self.toggle_button = tk.Button(
            root,
            text="Start",
            command=self.toggle,
            width=13,
            font=("Arial", -16, "bold"),
            pady=10,
            borderwidth=0,
        )
        self.toggle_button.place(relx=0.5, rely=1, y=-24, anchor="s")
        self.theme_button = tk.Button(
            root,
            command=self.toggle_theme,
            relief="flat",
            borderwidth=0,
            font=("Arial", -24),
            width=2,
        )
        self.theme_button.place(relx=1, x=-8, y=8, anchor="ne")
        self.base_fonts = {
            widget: root.tk.splitlist(widget.cget("font"))
            for widget in (
                self.title_label,
                self.time_label,
                self.toggle_button,
                self.theme_button,
            )
        }
        root.bind("<Configure>", self.resize_interface)
        self.apply_theme()

        root.protocol("WM_DELETE_WINDOW", self.close)
        self.tick()

    def resize_interface(self, event: tk.Event) -> None:
        if event.widget is not self.root:
            return
        # Uniform scaling preserves the proportions of text and controls.
        # Use the shorter side so wide/tall windows do not stretch the UI.
        scale = min(event.width, event.height) / 300
        for widget, font in self.base_fonts.items():
            widget.configure(
                font=(
                    font[0],
                    -max(1, round(abs(int(font[1])) * scale)),
                    *font[2:],
                )
            )
        self.title_label.place_configure(x=round(16 * scale), y=round(28 * scale))
        self.toggle_button.configure(padx=round(3 * scale), pady=round(10 * scale))
        self.toggle_button.place_configure(y=-round(24 * scale))
        self.theme_button.place_configure(x=-round(8 * scale), y=round(8 * scale))

    def toggle_theme(self) -> None:
        self.dark_mode = not self.dark_mode
        self.apply_theme()

    def apply_theme(self) -> None:
        colors = THEMES["dark" if self.dark_mode else "light"]
        self.root.configure(bg=colors["bg"])
        for widget in self.root.winfo_children():
            widget.configure(bg=colors["bg"], fg=colors["fg"])
            if isinstance(widget, tk.Button):
                widget.configure(
                    activebackground=colors["hover"],
                    activeforeground=colors["fg"],
                    highlightbackground=colors["bg"],
                )
        color = colors["accent" if self.session_id is None else "stop"]
        self.toggle_button.configure(
            bg=color, activebackground=color, fg="white", activeforeground="white"
        )
        self.theme_button.configure(text="☀" if self.dark_mode else "☾")

    def toggle(self) -> None:
        now = self.clock()
        if self.session_id is None:
            self.session_id = db_start_session(self.db, now)
            label = "Stop"
        else:
            db_update_session(self.db, self.session_id, now)
            self.session_id = None
            label = "Start"
        self.toggle_button.configure(text=label)
        self.apply_theme()
        self.update_display()

    def update_display(self) -> None:
        now = self.clock()
        if self.session_id is not None:
            db_update_session(self.db, self.session_id, now)
        used = time_used(
            db_load_intervals(self.db), TimeInterval(now - SLIDING_WINDOW, now)
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
        App(root, db)
        root.mainloop()


if __name__ == "__main__":
    main()
