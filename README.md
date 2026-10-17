# ⚡ YouTube Ultra Downloader [Gothic Crimson Edition]

A production-grade desktop application for **yt-dlp** and **FFmpeg** featuring dark gothic and crimson aesthetic backgrounds, built for long-term Windows stability and zero-maintenance operation.

---

## 🛡️ Enterprise Stability, Windows Resilience & Full Privacy

### 1. 🔒 100% Privacy & Data Security
- **No Background Clipboard Sniffing**: The app never scans or reads your clipboard in the background on startup. Clipboard access is strictly user-triggered (via the **"📋 Paste Link"** button or pressing **Ctrl+V**).
- **Zero Telemetry / No Tracking**: No external analytics, telemetry, or user metrics are transmitted anywhere.
- **No Residual Cache**: Operations run with `--no-cache-dir` and isolated temporary files to prevent cookie or tracking retention on disk.

### 2. ⚡ YouTube Update Proofing (1-Click Engine Update)
- YouTube frequently alters its cipher and video delivery algorithms.
- With the built-in **"⚡ Update Engine"** button in the header, you can upgrade `yt-dlp` to the latest upstream release in seconds with one click. You will never be left with broken downloads when YouTube changes things.

### 3. 🖥️ Windows Update & High-DPI Resilience
- **Per-Monitor High-DPI Aware**: Automatically scales razor-sharp on 4K, 1440p, and multi-monitor setups without blurriness or distortion.
- **Dynamic Portable Pathing**: Zero hardcoded usernames (`C:\Users\...`). Settings and downloads dynamically adapt to your Windows environment (`%APPDATA%`, `%LOCALAPPDATA%`, and `~/Downloads/downloder`).
- **Clean Process Tree Termination**: Exiting the app or clicking **"⏹️ Stop"** uses Windows `taskkill /F /T` to kill both `yt-dlp` and any child `ffmpeg` processes, guaranteeing zero orphaned background tasks or file locks.
- **Windows-Safe Filenames**: Includes `--windows-filenames` enforcement so special characters in video titles never cause NTFS filesystem errors.

---

## 🎨 Theme Backgrounds Included
- 💀 **The Strain (Crimson Skull & Mist)**: High-contrast dark red gothic skull aesthetic.
- 🌹 **Gothic Rose (Dark Crown & Veil)**: Deep black veil, dark crown, and floating rose petals.
- 🌑 **Obsidian Dark**: Stealth minimalist black mode.

Toggle between themes at any time using the theme switcher in the top-right corner.

---

## 🚀 Quality Modes (Your Exact Commands)

- 🌟 **4K / Max Quality**:
  `yt-dlp -f "bv*+ba/b" --merge-output-format mp4 "<URL>"`
- 🖥️ **1080p Full HD**:
  `yt-dlp -f "bestvideo*[height<=1080]+bestaudio/best[height<=1080]" --merge-output-format mp4 "<URL>"`
- 📱 **720p HD (Fast Download)**:
  `yt-dlp -f "bestvideo*[height<=720]+bestaudio/best[height<=720]" --merge-output-format mp4 "<URL>"`
- 🎵 **Audio Only (MP3 Extraction)**:
  `yt-dlp -f "bestaudio/best" -x --audio-format mp3 "<URL>"`

---

## 🖥️ How to Launch

1. **Desktop Shortcut**: Double-click the **`YouTube Downloader Ultra`** icon on your **Desktop**.
2. **Standalone Executable**: Run `dist\YouTube_Downloader\YouTube_Downloader.exe`.
3. **Batch Launcher**: Double-click `Launch_Downloader.bat`.
