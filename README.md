# ai-voice-usage

A small Python app for manually monitoring **ChatGPT Voice usage** over a sliding time window.

Track how much time you have spent using ChatGPT Voice in the last N hours. Press **Start** to track a session and **Stop** to save it. The total updates automatically as older sessions leave the window. You can change the window size directly in the app.

## Motivation

Shouldn’t the ChatGPT interface provide this information? Yes, it should, but apparently it doesn’t (last checked on October 24, 2026). Until this UX issue is fixed, I’ll use this.

## Requirements

- **Python 3.12+** with `tkinter` and sqlite3 support (generally it comes pre-installed).

The app is designed to work on **Linux, Windows, and macOS**, wherever Tkinter is available.

## Run

```sh
python3 ai_voice_usage.py
```

Sessions are stored in a SQLite3 database and the window setting in TOML, under `~/.ai-voice-usage/` (your home directory).

## Philosophy

One Python file, roughly 200 lines, and only the standard library. The point is to be **simple, useful, and easy to hack on**
