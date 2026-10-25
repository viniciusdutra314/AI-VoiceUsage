# AI-VoiceUsage

A small Python app for manually monitoring **ChatGPT Voice usage** over a sliding time window.

Track how much time you have spent using ChatGPT Voice in the last 24 hours. Press **Start** to track a session and **Stop** to save it. The total updates automatically as older sessions leave the window. A compact **Stats** button opens a 24-hour recovery forecast; the main window supports Dark and Light themes.

## Download

Download the executable for your operating system and architecture. No installation is needed. The executable is self-contained and can be moved wherever you like.

| Operating system | x64 (Intel / AMD) | ARM64 |
| --- | --- | --- |
| <img src="assets/windows.png" width="20" height="20" alt=""> Windows | [Download .exe](https://github.com/viniciusdutra314/ai-voice-usage/releases/latest/download/AI-VoiceUsage-windows-x64.exe) | [Download .exe](https://github.com/viniciusdutra314/ai-voice-usage/releases/latest/download/AI-VoiceUsage-windows-arm64.exe) |
| <img src="assets/macos.png" width="20" height="20" alt=""> macOS | [Download](https://github.com/viniciusdutra314/ai-voice-usage/releases/latest/download/AI-VoiceUsage-macos-x64) | [Download (Apple Silicon)](https://github.com/viniciusdutra314/ai-voice-usage/releases/latest/download/AI-VoiceUsage-macos-arm64) |
| <img src="assets/linux.png" width="20" height="20" alt=""> Linux | [Download](https://github.com/viniciusdutra314/ai-voice-usage/releases/latest/download/AI-VoiceUsage-linux-x64) | [Download](https://github.com/viniciusdutra314/ai-voice-usage/releases/latest/download/AI-VoiceUsage-linux-arm64) |

Sessions are saved in `time_intervals.sqlite3` in the following folder:

- **Windows:** `%LOCALAPPDATA%\AI-VoiceUsage\` (paste this path into the File Explorer address bar).
- **Linux and macOS:** `~/.ai-voice-usage/` (`~` is your home directory).

The database is stored separately from the executable, so moving it does not move your data.

## Motivation

Shouldn’t the ChatGPT interface provide this information? Yes, it should, but apparently it doesn’t (last checked on October 24, 2026). Until this UX issue is fixed, I’ll use this.

The app keeps things simple: one Python file (~200 lines) and only the standard library. The point is to be **simple, useful, and easy to hack on**.
