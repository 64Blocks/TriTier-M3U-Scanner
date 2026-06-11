```markdown
# TriTier-M3U-Scanner

[![Python](https://img.shields.io/badge/Python-3.8+-3776AB.svg?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![UI](https://img.shields.io/badge/UI-CustomTkinter-1E1E1E.svg?style=flat-square&logo=python&logoColor=white)](https://github.com/TomSchimansky/CustomTkinter)
[![License](https://img.shields.io/badge/License-MIT-2DA446.svg?style=flat-square)]()

A professional-grade IPTV playlist scanner and validator. This tool evaluates M3U streams using a multi-threaded, 3-tier testing engine powered by FFmpeg to measure latency, frame stability, and codec validity. It maintains a resilient local database to track domain health, profile network conditions, and generate optimized, filtered, and smartly categorized playlists.

## ✨ Key Features

* **3-Tier Smart Testing Engine**: Balances speed and accuracy with Connectivity, Segment, and FFmpeg decoding checks.
* **Network Profiling**: Automatically tests sample URLs to determine the optimal timeout and FFmpeg duration for your specific network conditions.
* **Raw DNS Performance Tester**: Built-in tool to test and rank global and regional DNS servers based on your actual M3U playlist domains.
* **Host Ranking System**: Analyzes and ranks IPTV providers/domains based on the quantity and quality of healthy channels.
* **Smart Categorization & Emojis**: Automatically categorizes channels (Sport, News, Movie, etc.) and adds relevant emojis to the exported `clean.m3u`.
* **Matrix/Hacker UI**: A sleek, dark-mode, terminal-style GUI built with CustomTkinter, featuring real-time progress tracking, pause/resume capabilities, and live logs.
* **Resilient Domain Backoff**: Prevents IP bans by dynamically backing off from failing or timing-out domains.
* **VPN/Proxy Detection**: Automatically detects and displays your public IP and active VPN/Proxy status in the UI header.

## 📦 Installation

This project requires Python 3.8 or higher. External binaries are required for deep stream analysis.

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```
2. **Create and activate a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. **Install Python dependencies**:
   ```bash
   pip install customtkinter
   ```
4. **Install external binaries**:
   - **[FFmpeg & FFprobe](https://ffmpeg.org/)**: Must be installed and available in your system `PATH`, or placed at `C:\ffmpeg\bin\`.
   - **[VLC Media Player](https://www.videolan.org/vlc/)**: Required for the manual testing workflow. Expected at standard Windows installation paths.

## ⚙️ The 3-Tier Smart Testing Engine

The core of this application is its multi-stage validation engine, designed to balance speed with absolute accuracy. Channels are scored up to 100 points based on the following tiers:

* **Level 1 (L1) - Connectivity Check (25 pts)**: Validates basic HTTP response headers and measures initial connection latency by fetching a minimal payload (1024 bytes).
* **Level 2 (L2) - Segment Resolution (25 pts)**: Parses HLS manifests (`.m3u8`), follows redirect chains up to three depths, and verifies that actual media segments are reachable and responsive.
* **Level 3 (L3) - FFmpeg Stream Analysis (50 pts)**: Invokes `ffmpeg` via `subprocess` to decode a short, timed payload. It evaluates frame counts, processed time, and decode errors to confirm actual stream stability without downloading the entire file.
* **Deep Mode (FFprobe Bonus +10 pts)**: Optionally invokes `ffprobe` to explicitly validate `video` and `audio` codec types, adding a scoring bonus for streams with verified media tracks.

*Note: The final score is strictly capped at 100 to maintain consistent data integrity.*

## 🛠️ Interesting Techniques

* **Smart Domain Backoff & Resilience**: Implements a dynamic cooldown and scoring system. If a domain fails repeatedly, the system increases the delay between requests, preventing IP bans and managing failing endpoints gracefully.
* **Dynamic User-Agent Rotation**: Rotates through a list of verified User-Agent strings (including VLC, ExoPlayer, and modern browsers) to prevent stream providers from blocking automated requests.
* **Raw DNS Resolution Testing**: Constructs raw DNS query packets using Python’s `struct` module to measure UDP latency to various DNS resolvers. This bypasses external CLI tools and OS-level caching, providing direct, low-level network performance metrics.
* **Batch Database Writing**: Utilizes batch writing techniques to save large M3U and JSON databases instantly, preventing UI freezes and file corruption during intensive operations.
* **Asynchronous Queue Management**: Utilizes Python’s `queue.Queue` and `concurrent.futures.ThreadPoolExecutor` to decouple the graphical user interface from heavy I/O operations, ensuring the UI remains fully responsive and crash-free.

## 🔌 Non-Obvious Technologies & Libraries

* **[CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)**: A modern, themed UI library for Python used here to create the "Matrix" dark-mode interface.
* **FFmpeg & FFprobe**: Invoked via `subprocess` for deep stream analysis, codec detection, and decode error tracking.
* **VLC Media Player**: Integrated directly into the manual testing workflow for real-time, human-verified stream playback.
* **`struct` Module**: Used for low-level binary packing to manually craft and send DNS query packets over UDP.
* **`concurrent.futures`**: Used for robust, crash-free multi-threading during auto health checks.

## 🔗 External Dependencies & Fonts

* **CustomTkinter**: [GitHub Repository](https://github.com/TomSchimansky/CustomTkinter)
* **FFmpeg / FFprobe**: [Official Website](https://ffmpeg.org/)
* **VLC Media Player**: [Official Website](https://www.videolan.org/vlc/)
* **Font**: The UI relies on **Lucida Console** for its terminal-like aesthetic, with standard system monospace fallbacks.

## 📂 Project Structure

```text
TriTier-M3U-Scanner/
│
├── main.py                  # Minimal entry point (Launches the GUI)
├── config.py                # Global settings, default paths, and configurations
│
├── gui/                     # User Interface Layer
│   ├── app.py               # 🧠 Orchestrator: Manages state, queues, threads, and coordinates modules
│   ├── tabs.py              # 🎨 UI Builder: Constructs widgets and binds buttons to app.py methods
│   ├── theme.py             # 🎨 Matrix theme settings (Colors, fonts, CustomTkinter config)
│   ├── health_checker.py    # ⚙️ Auto Health Check: Manages multi-threaded workers, scoring, and batch saving
│   ├── manual_tester.py     # ⚙️ Manual Tester: Manages VLC playback, user feedback dialogs, and retry.m3u
│   ├── profile_manager.py   # ⚙️ Profile Manager: Parses URLs, runs background network tests, manages profiles.json
│   └── live_db_manager.py   # ⚙️ Live DB Manager: Loads, filters, edits, and deletes verified channels in UI
│
├── core/                    # Headless Logic & Processing Layer
│   ├── engine.py            # 🚀 Testing Core: Implements test_channel_smart (L1, L2, L3, Probe)
│   ├── backoff.py           # 🛡️ Smart Domain State: Manages cooldowns, resilience scores, and fail tracking
│   └── dns_tester.py        # 🌐 DNS Tester: Independent tool for testing DNS server speed and stability
│
├── database/                # Data Persistence Layer
│   ├── manager.py           # 💾 Optimized Load/Save: Uses batch writing to prevent crashes and UI freezes
│   └── parser.py            # 📝 Helper functions for parsing raw M3U text content
│
├── utils/                   # Utilities
│   └── helpers.py           # 🛠️ FFmpeg/VLC path detection, random UA generation, smart categorization, VPN detection
│
└── output/                  # 📁 Output Directory (Auto-generated)
    ├── clean.m3u            # Final list of healthy, smartly categorized channels with emojis
    ├── health_check.m3u     # Full list of scanned channels with scores (sorted by quality)
    ├── retry.m3u            # List of channels flagged for manual retry
    └── app_log.txt          # Timestamped log of all application activities
```

### Directory Descriptions
* **[output/](output/)**: Contains all runtime-generated artifacts. `clean.m3u` is the primary deliverable for end-use, featuring smart categorization and emojis. `health_check.m3u` retains granular scoring data (e.g., `90/100 ⭐⭐⭐⭐⭐`) for historical tracking and prevents data loss between sessions.
* **[backup/](backup/)**: Safeguards previous iterations of `clean.m3u` before destructive updates or major testing runs.

---
*Made with ❤️ by x64 block*
```