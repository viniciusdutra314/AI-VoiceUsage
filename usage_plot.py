"""Small Tkinter-only forecast of usage in the next rolling window."""

import math
import tkinter as tk
from datetime import datetime, timedelta


def forecast_points(intervals, now: datetime, window: timedelta):
    """Vertices of future usage, assuming the recording stops now."""
    sessions = [(item.start, min(item.end, now)) for item in intervals
                if item.start <= now and item.end > now - window]
    horizon = now + window
    times = {now, horizon}
    for start, end in sessions:
        for t in (start + window, end + window):
            if now < t < horizon:
                times.add(t)

    def usage_at(t):
        return sum((max(timedelta(), end - max(start, t - window))
                    for start, end in sessions), timedelta())

    return [(t, usage_at(t)) for t in sorted(times)]


class StatisticsWindow:
    def __init__(self, parent, colors):
        self.window = tk.Toplevel(parent)
        self.window.title("AI-VoiceUsage — Statistics")
        self.window.geometry("680x350")
        self.window.minsize(450, 260)
        self.label = tk.Label(self.window, text="Voice usage · next 24 hours",
                              font=("Arial", 12, "bold"), pady=15)
        self.label.pack(fill="x")
        self.canvas = tk.Canvas(self.window, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.canvas.bind("<Configure>", lambda _: self.draw())
        self.colors = colors
        self.points = []
        self.ends = []
        self.now = None
        self.window_length = None
        self.apply_theme(colors)

    def apply_theme(self, colors):
        self.colors = colors
        self.window.configure(bg=colors["bg"])
        self.label.configure(bg=colors["bg"], fg=colors["fg"])
        self.canvas.configure(bg=colors["bg"])
        self.draw()

    def render(self, intervals, now, window):
        intervals = tuple(intervals)
        self.now, self.window_length = now, window
        self.points = forecast_points(intervals, now, window)
        self.ends = sorted({min(item.end, now) + window for item in intervals
                            if item.start <= now})
        self.draw()

    def draw(self):
        c = self.canvas
        c.delete("all")
        if not self.points:
            return
        p = self.colors
        width, height = max(c.winfo_width(), 450), max(c.winfo_height(), 220)
        left, right, top, bottom = 81, width - 18, 15, height - 49
        peak = max(1800, math.ceil(self.points[0][1].total_seconds() / 1800) * 1800)
        now, window = self.now, self.window_length

        def x(t):
            return left + (t - now) / window * (right - left)

        def y(duration):
            return bottom - duration.total_seconds() / peak * (bottom - top)

        def duration_label(seconds):
            minutes = round(seconds / 60)
            return f"{minutes // 60}h{minutes % 60:02d}"

        for fraction in (0, 0.5, 1):
            yy = bottom - fraction * (bottom - top)
            c.create_line(left, yy, right, yy, fill=p["grid"], dash=(2, 3))
            c.create_text(left - 7, yy, anchor="e", text=duration_label(peak * fraction),
                          fill=p["muted"], font=("Arial", 9))

        xy = [value for t, duration in self.points for value in (x(t), y(duration))]
        c.create_polygon([left, bottom, *xy, right, bottom], fill=p["hover"], outline="")
        c.create_line(xy, fill=p["accent"], width=2)
        c.create_line(left, top, left, bottom, right, bottom, fill=p["muted"])
        c.create_text(left, bottom + 15, anchor="w",
                      text=now.astimezone().strftime("%H:%M") + " now",
                      fill=p["muted"], font=("Arial", 9))

        last_x = left + 52
        for t in self.ends:
            if not now < t < now + window:
                continue
            xx = x(t)
            if xx - last_x < 57 or xx > right - 24:
                continue  # A close label may be omitted; the curve remains exact.
            last_x = xx
            c.create_line(xx, top, xx, bottom, fill=p["grid"], dash=(2, 3))
            c.create_text(xx, bottom + 15, text=t.astimezone().strftime("%H:%M"),
                          fill=p["muted"], font=("Arial", 9))
