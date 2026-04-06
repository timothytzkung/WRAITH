# HAUNTED BROWSER — W R A I T H

> *"I can already feel the data."*

A horror experience powered by a local LLM. WRAITH reads your browser history and speaks it back to you through an unsettling, autonomous AI persona. Built on a **Belief-Desire-Intention (BDI) agent architecture**, WRAITH deliberates, forms intentions, and acts on them.

---

## ⚠️ DISCLAIMER — FULL SYSTEM ACCESS & USER CONSENT

**BY RUNNING THIS SOFTWARE, YOU EXPLICITLY ACKNOWLEDGE AND ACCEPT THE FOLLOWING:**

This program requires and will actively use **full disk access** on your computer. Specifically, it will:

- **Read your browser history** directly from disk (Chrome, Brave, Safari, and Firefox profile databases)
- **Read files on your Desktop and in your Downloads folder** as part of the WRAITH experience
- **Write files to your Desktop** (WRAITH may leave files behind as part of the horror narrative)
- **Take screenshots** of your screen at any time during the experience
- **Control your mouse cursor** — moving it autonomously across your screen
- **Type keyboard input** into your active window via automated input injection
- **Open applications and URLs** in your default browser or Terminal

This software is an **interactive horror art project**. All of the above actions are intentional features, not bugs. They are designed to create an unsettling experience by making the AI feel invasive and real.

**By running `run.py`, you accept that:**
1. You grant this software full read/write access to your personal computer and files.
2. You consent to the software reading, referencing, and displaying your private browser history.
3. You consent to autonomous manipulation of your cursor, keyboard, and screen.
4. You consent to files being written to your Desktop by the program.
5. You consent to screenshots being taken and saved to your Desktop.
6. **You take full responsibility for any consequences** of running this software on your machine.
7. This software is provided **as-is**, with no warranty of any kind.

> **If you do not agree to these terms, do not run this program.**

To abort the experience at any time, **move your mouse to the top-left corner of your screen** (PyAutoGUI failsafe).

---

## What Is This?

HAUNTED BROWSER is a macOS desktop application that:

1. Silently scans your browser history (Brave by default; Chrome, Safari, Firefox supported)
2. Initializes a **WRAITH BDI agent** that forms beliefs about you based on what it finds
3. Connects to a locally running **Ollama** LLM (`mistral-nemo` by default) to generate eerie, personalized dialogue
4. Speaks responses aloud using a creepy text-to-speech voice (SAM TTS)
5. Executes real agentic side-effects — cursor possession, file drops, screenshots — to blur the line between software and haunting

---

## Features

- **BDI Agent Architecture** — WRAITH has Beliefs (your history, emotional state, turn count), Desires (intimidate, expose, taunt, possess, etc.), and Intentions (the chosen plan each turn)
- **Adaptive behavior** — WRAITH responds differently based on whether you seem calm, curious, scared, or defiant
- **Real side-effects** — cursor spirals, desktop file drops, screenshots, keyboard typing
- **Multi-browser support** — Brave, Chrome, Safari, Firefox
- **Glitchy typewriter UI** — text renders character-by-character with occasional glyph corruption
- **URL ticker** — your browser history scrolls across the bottom of the window
- **Interactive chat** — you can type back to WRAITH and it will react

---

## Requirements

- **macOS** (the app uses `osascript`, `open -a`, and macOS-specific browser profile paths)
- **Python 3.10+**
- **Ollama** running locally at `http://127.0.0.1:11434` with the `mistral-nemo` model pulled
- **Full Disk Access** granted to your Terminal/Python interpreter in System Settings

### Python Dependencies

```
pip install requests pyautogui samtts
```

> `tkinter` is included with most Python distributions. If missing, install via your package manager.

---

## macOS Full Disk Access

This app **will not work** without Full Disk Access. To grant it:

1. Open **System Settings → Privacy & Security → Full Disk Access**
2. Enable access for your **Terminal** application (or whichever app you use to run Python)
3. Restart your terminal session

Without this, the browser history SQLite databases will be unreadable.

---

## Setup & Running

```bash
# 1. Pull the required Ollama model
ollama pull mistral-nemo

# 2. Start Ollama (if not already running)
ollama serve

# 3. Install Python dependencies
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Run the experience
python run.py
```

---

## Configuration

At the top of `main.py`, you can adjust the following constants:

| Constant | Default | Description |
|---|---|---|
| `OLLAMA_MODEL` | `"mistral-nemo"` | The Ollama model to use |
| `OLLAMA_URL` | `http://127.0.0.1:11434/api/chat` | Ollama API endpoint |
| `MAX_HISTORY` | `80` | Number of history entries to load per browser |
| `MAX_WAIT_TIME` | `300` | LLM request timeout in seconds |

To enable additional browsers, uncomment the relevant lines in the `gather_history()` function:

```python
def gather_history():
    history = []
    # history += get_chrome_history()
    history += get_brave_history()       # ← currently active
    # history += get_safari_history()
    # history += get_firefox_history()
    return history
```

---

## Architecture Overview

```
HauntedApp (tkinter UI)
    └── WraithBDI (BDI Agent)
            ├── Beliefs: history, conversation, user_emotion, turn, used_actions
            ├── Desires: destabilise, expose, taunt, intimidate, possess_cursor,
            │           read_your_files, leave_a_mark, go_silent, finale
            └── Intentions → WraithTools (side-effect executor)
                                ├── read_recent_files()
                                ├── list_downloads()
                                ├── write_file()
                                ├── take_screenshot()
                                ├── move_cursor_ominously()
                                ├── cursor_spiral()
                                ├── type_message()
                                └── open_application() / open_url()
```

Each turn, WRAITH:
1. **Deliberates** — selects an intention from currently applicable desires
2. **Executes side-effects** — performs the real-world action (if any) for that intention
3. **Builds a prompt** — injects browser history, emotional state, and tool results into the LLM context
4. **Generates a response** — calls Ollama and receives WRAITH's reply
5. **Updates beliefs** — revises internal state based on what was said and how the user reacted

---

## Safety & Abort

- **Mouse failsafe**: Moving your cursor to the **top-left corner** of the screen will immediately raise a `FailSafeException` and halt any automated cursor movement (PyAutoGUI built-in).
- All agentic actions run in **daemon threads** and will stop when the application is closed.
- WRAITH does **not** send any data to external servers. All LLM inference runs locally via Ollama.
- The only files written to disk are those explicitly created by the `leave_a_mark` action on your Desktop, and screenshots saved as `wraith_sees.png` on your Desktop.

---

## License

This project is provided for educational and artistic purposes. No warranty is provided. Use at your own risk.