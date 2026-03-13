
# 👻 HAUNTED BROWSER — Setup Guide
 
A horror game-like experience where a local AI reads your browser history
and speaks it back to you through an unsettling persona called **WRAITH**.
 
---
 
## Requirements
 
### 1. Python dependencies
```bash
pip3 install requirements.txt
```
*(tkinter is included with macOS Python)*
 
### 2. Ollama (local LLM)
```bash
# Install Ollama
brew install ollama
 
# Pull a model (mistral-nemo recommended)
ollama pull mistral-nemo
 
```
 
 
## Configuration (edit top of haunted_browser.py)
 
```python
OLLAMA_MODEL = "mistral-nemo"               # Your pulled model
PIPER_BIN    = "piper"                     # Path to piper binary
PIPER_MODEL  = "en_US-amy-medium.onnx"    # Path to voice model
MAX_HISTORY  = 60                          # URLs to feed the LLM
```
 
---
 
## macOS Permissions Required
 
macOS will ask for permission to access browser databases.
Go to **System Settings → Privacy & Security → Full Disk Access**
and grant access to **Terminal** (or whichever app runs the script).
 
Browsers supported:
- **Chrome** — `~/Library/Application Support/Google/Chrome/Default/History`
- **Safari** — `~/Library/Safari/History.db`
- **Firefox** — `~/Library/Application Support/Firefox/Profiles/*/places.sqlite`
 
---
 
## Run
 
```bash
python run.py
```
 
`ollama serve` will automatically run as a subprocess.
 
---
 
## How It Works
 
1. On launch, the app copies (read-only) your browser history SQLite databases
2. Extracts the last ~60 URLs across Chrome, Safari, and Firefox
3. Sends them to your local Ollama model with a horror persona prompt (WRAITH)
4. The response is displayed with a glitchy typewriter effect
5. Piper TTS reads it aloud simultaneously (work in progress)
6. Four escalating phases: **intro → reveal → taunt → finale**
 
---

 
## ⚠️ Privacy Note
 
This app **only reads your history locally** and sends it to your **local Ollama instance**.
Nothing leaves your machine. No data is uploaded anywhere.