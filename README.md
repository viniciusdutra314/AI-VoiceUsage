# ai-voice-usage

A small Python app for manually monitoring **ChatGPT Voice usage** over a sliding time window.

Track how much time you have spent using ChatGPT Voice in the last N hours. Press **Start** to track a session and **Stop** to save it. The total updates automatically as older sessions leave the window. You can change the window size directly in the app.

## Download

Download the executable for your operating system and architecture. No installation is needed. The executable is self-contained and can be moved wherever you like.

| Operating system | x64 (Intel / AMD) | ARM64 |
| --- | --- | --- |
| <img src="assets/windows.png" width="20" height="20" alt=""> Windows | [Download .exe](https://github.com/viniciusdutra314/ai-voice-usage/releases/latest/download/ai-voice-usage-windows-x64.exe) | [Download .exe](https://github.com/viniciusdutra314/ai-voice-usage/releases/latest/download/ai-voice-usage-windows-arm64.exe) |
| <img src="assets/macos.png" width="20" height="20" alt=""> macOS | [Download](https://github.com/viniciusdutra314/ai-voice-usage/releases/latest/download/ai-voice-usage-macos-x64) | [Download (Apple Silicon)](https://github.com/viniciusdutra314/ai-voice-usage/releases/latest/download/ai-voice-usage-macos-arm64) |
| <img src="assets/linux.png" width="20" height="20" alt=""> Linux | [Download](https://github.com/viniciusdutra314/ai-voice-usage/releases/latest/download/ai-voice-usage-linux-x64) | [Download](https://github.com/viniciusdutra314/ai-voice-usage/releases/latest/download/ai-voice-usage-linux-arm64) |

## Motivation

Shouldn’t the ChatGPT interface provide this information? Yes, it should, but apparently it doesn’t (last checked on October 24, 2026). Until this UX issue is fixed, I’ll use this.

## Requirements

- **Python 3.12+** with `tkinter` and `sqlite3` support (usually included with Python).

The app is designed to work on **Linux, Windows, and macOS**, wherever Tkinter is available.

## Run

```sh
python3 ai_voice_usage.py
```

Sessions are stored in a SQLite3 database, and the window setting is stored in a TOML file, both under `~/.ai-voice-usage/` in your home directory.

## Philosophy

One Python file, roughly 200 lines, and only the standard library. The point is to be **simple, useful, and easy to hack on**.
