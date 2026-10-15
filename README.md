# Rolling Timer

A tiny, fully functional **sliding-window time tracker** written in Python.

Traditional clock apps such as [GNOME Clocks](https://apps.gnome.org/en/Clocks/) and [KDE Clock](https://apps.kde.org/kclock/) provide stopwatches and countdown timers, but don't offer rolling-window usage tracking as a documented feature. Rolling Timer fills that little gap: it shows **how much time you've used in the last N hours**.

#[showcase_img]

Press **Start** to track a session and **Stop** to save it. The total updates automatically—even while stopped, as older sessions leave the window. You can change the window size directly in the app.

## Requirements

- **Python 3.12+** with `tkinter` support (generally it comes pre-installed, check with `python -m tkinter`).

The app is designed to work on **Linux, Windows, and macOS**, wherever Tkinter is available.

## Run

```sh
python3 rolling_timer.py
```

Sessions are stored in JSON Lines and the window setting in TOML, under `~/.rolling_timer/` (your home directory).

## Philosophy

One Python file, roughly 200 lines, and only the standard library. The point is to be **simple, useful, and easy to hack on**: read it, change it, break it, learn from it.
