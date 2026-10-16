# NGL Blaster 🚀

A fast, multithreaded desktop tool and CLI utility for sending automated anonymous messages to NGL.link targets.

## Features

- **Modern Dark GUI**: CustomTkinter-based interface with macOS-styled controls, responsive dark theme, and real-time activity console.
- **Live Metrics Dashboard**: Real-time tracking of sent messages, total duration, request times, and overall progress.
- **Multithreading**: Configurable thread concurrency for high-efficiency throughput.
- **Unlimited Mode**: Continuous message generation with randomized positive compliments and safety error handling.
- **CLI Mode**: Standalone command-line script (`ngl_bot.py`) for headless/server environments.

---

## Installation

1. **Clone the repository**:
   ```bash
   git clone <YOUR_REPOSITORY_URL>
   cd <REPOSITORY_FOLDER>
   ```

2. **Set up virtual environment (optional but recommended)**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

---

## Usage

### 1. GUI Application
Launch the GUI application:
```bash
python3 ngl_gui.py
```
- Enter your target link: `https://ngl.link/[USERNAME]`
- Adjust the number of messages, threads, and inter-request delay (ms).
- Toggle **∞ UNLIMITED** mode if you wish to run continuously.
- Click **▶ START** to begin or **⏹ STOP** to interrupt anytime.

### 2. Command-Line Interface (CLI)
Run directly via the terminal:

- Send a specific number of messages (e.g. 50 messages across 5 threads):
  ```bash
  python3 ngl_bot.py --url https://ngl.link/TARGET_USER --messages 50 --threads 5 --delay 100
  ```

- Send unlimited messages continuously:
  ```bash
  python3 ngl_bot.py --url https://ngl.link/TARGET_USER --unlimited --threads 5 --delay 100
  ```

---

## Disclaimer
This project is for educational and testing purposes only. Please respect platform terms of service and avoid harassment or abuse.
