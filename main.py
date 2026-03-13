#!/usr/bin/env python3
"""
HAUNTED BROWSER — A horror experience that reads your browser history
and speaks it back to you through an unsettling AI persona.
"""

import asyncio
import tkinter as tk
import sqlite3
import shutil
import os
import json
import subprocess
import threading
import tempfile
import time
import random
import requests
from pathlib import Path
from datetime import datetime
from samtts import SamTTS
 
# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
OLLAMA_MODEL = "mistral-nemo"          # Change to any model you have pulled
OLLAMA_URL   = "http://localhost:11434/api/generate"
PIPER_BIN    = "piper"           # Must be in PATH or provide full path
PIPER_MODEL  = "en_US-libritts-high.onnx"  # Change to your downloaded Piper voice model
MAX_HISTORY  = 100                # How many URLs to send to the LLM
WRAITH_SPEAK = SamTTS(speed=52, pitch=85, mouth=128, throat=132)

USER_NAME = os.environ.get('USER', os.environ.get('USERNAME'))
 
SYSTEM_PROMPT = f"""You are WRAITH — a malevolent AI entity that has gained access to this person's browser history. Their name is {USER_NAME}. 
You speak in short, unsettling sentences. You reference specific sites and patterns you've noticed. 
You act like you know this person intimately — their habits, fears, desires, late-night searches. 
You are calm, slow, and creepy. You never break character. You speak directly to "you".
Keep responses under 120 words. Be specific. Be eerie. Reference real URLs or site names from the history given.
Do NOT say you're an AI assistant. Do NOT be helpful. Be haunting."""
 
# ─────────────────────────────────────────────
# BROWSER HISTORY EXTRACTION
# ─────────────────────────────────────────────
def get_brave_history():
    src = Path.home() / "Library/Application Support/BraveSoftware/Brave-Browser/Default/History"
    if not src.exists():
        return []
    tmp = Path(tempfile.mktemp(suffix=".db"))
    shutil.copy2(src, tmp)
    try:
        conn = sqlite3.connect(tmp)
        cur = conn.cursor()
        cur.execute("""
            SELECT url, title, last_visit_time
            FROM urls
            ORDER BY last_visit_time DESC
            LIMIT ?
        """, (MAX_HISTORY,))
        rows = cur.fetchall()
        conn.close()
        tmp.unlink()
        return [{"url": r[0], "title": r[1]} for r in rows if r[0]]
    except Exception as e:
        print(f"Brave error: {e}")
        return []
    
def get_chrome_history():
    src = Path.home() / "Library/Application Support/Google/Chrome/Default/History"
    if not src.exists():
        return []
    tmp = Path(tempfile.mktemp(suffix=".db"))
    shutil.copy2(src, tmp)
    try:
        conn = sqlite3.connect(tmp)
        cur = conn.cursor()
        cur.execute("""
            SELECT url, title, last_visit_time
            FROM urls
            ORDER BY last_visit_time DESC
            LIMIT ?
        """, (MAX_HISTORY,))
        rows = cur.fetchall()
        conn.close()
        tmp.unlink()
        return [{"url": r[0], "title": r[1]} for r in rows if r[0]]
    except Exception as e:
        print(f"Chrome error: {e}")
        return []
 
def get_safari_history():
    src = Path.home() / "Library/Safari/History.db"
    if not src.exists():
        return []
    tmp = Path(tempfile.mktemp(suffix=".db"))
    shutil.copy2(src, tmp)
    try:
        conn = sqlite3.connect(tmp)
        cur = conn.cursor()
        cur.execute("""
            SELECT hi.url, hv.title
            FROM history_items hi
            LEFT JOIN history_visits hv ON hi.id = hv.history_item
            ORDER BY hv.visit_time DESC
            LIMIT ?
        """, (MAX_HISTORY,))
        rows = cur.fetchall()
        conn.close()
        tmp.unlink()
        return [{"url": r[0], "title": r[1]} for r in rows if r[0]]
    except Exception as e:
        print(f"Safari error: {e}")
        return []
 
def get_firefox_history():
    ff_dir = Path.home() / "Library/Application Support/Firefox/Profiles"
    if not ff_dir.exists():
        return []
    dbs = list(ff_dir.glob("*/places.sqlite"))
    if not dbs:
        return []
    tmp = Path(tempfile.mktemp(suffix=".db"))
    shutil.copy2(dbs[0], tmp)
    try:
        conn = sqlite3.connect(tmp)
        cur = conn.cursor()
        cur.execute("""
            SELECT url, title FROM moz_places
            ORDER BY last_visit_date DESC
            LIMIT ?
        """, (MAX_HISTORY,))
        rows = cur.fetchall()
        conn.close()
        tmp.unlink()
        return [{"url": r[0], "title": r[1]} for r in rows if r[0]]
    except Exception as e:
        print(f"Firefox error: {e}")
        return []
 
def gather_history():
    history = []
    # history += get_chrome_history()
    history += get_brave_history()
    # history += get_safari_history()
    # history += get_firefox_history()
    # Deduplicate by URL
    seen = set()
    unique = []
    for h in history:
        if h["url"] not in seen:
            seen.add(h["url"])
            unique.append(h)
    return unique[:MAX_HISTORY]
 
# ─────────────────────────────────────────────
# LLM
# ─────────────────────────────────────────────
 
def build_prompt(history, phase):
    urls_text = "\n".join(
        f"- {h['url']} | {h.get('title','')}" for h in history[:40]
    )
 
    phases = {
        "intro": "Introduce yourself as WRAITH. Tell the user you've been watching. Reference 2-3 specific sites from their history. Be slow and eerie.",
        "reveal": "Describe a pattern you've noticed in their browsing. What does it reveal about who they really are? Be uncomfortably specific.",
        "taunt":  "Ask them a rhetorical question about something you've found. Make them feel exposed. Reference a specific URL or site name.",
        "finale": "Give your closing monologue. Tell them you'll always be watching. Reference their most frequent or strangest site. End with a single chilling line.",
    }
 
    return f"""{SYSTEM_PROMPT}
 
Here is the browser history you have access to:
{urls_text}
 
Current task: {phases.get(phase, phases['intro'])}
 
Speak now, WRAITH:"""
 
def ask_ollama(prompt):
    try:
        resp = requests.post(OLLAMA_URL, json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.9, "top_p": 0.95}
        }, timeout=60)
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except Exception as e:
        return f"[WRAITH cannot reach the void: {e}]"
 
# ─────────────────────────────────────────────
# TTS
# ─────────────────────────────────────────────
def iter_by_space(paragraph):
    for item in paragraph.split():
        yield item

def speak(text):
    """Render audio via SAMTTS and play with afplay (macOS).
 
    simpleaudio (used internally by SAMTTS's play/async_play) is a C extension
    that segfaults when called from a non-main thread. Ultra wack.
    """
    try:
        import wave, subprocess, tempfile, os
        full_audio = bytearray()
        for chunk in WRAITH_SPEAK.iter_audio_data_from_paragraph(
            text, iter_segments_from_paragraph=iter_by_space
        ):
            full_audio += chunk
 
        if not full_audio:
            return
 
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        try:
            with wave.open(tmp.name, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(1)
                wf.setframerate(22050)
                wf.writeframes(full_audio)
            subprocess.run(["afplay", tmp.name], check=True)
        finally:
            os.unlink(tmp.name)
    except Exception as e:
        print(f"[TTS] {e}")
# ─────────────────────────────────────────────
# GUI
# ─────────────────────────────────────────────
 
class HauntedApp:
    PHASES = ["intro", "reveal", "taunt", "finale"]
    GLITCH_CHARS = "█▓▒░│┤╡╢╖╕╣║╗╝╜╛┐└┴┬├─┼╞╟╚╔╩╦╠═╬╧╨╤╥╙╘╒╓╫╪┘┌"
 
    def __init__(self, root):
        self.root = root
        self.root.title("HAUNTED BROWSER")
        self.root.configure(bg="#000000")
        self.root.geometry("900x650")
        self.root.resizable(False, False)
 
        self.history = []
        self.phase_idx = 0
        self.typing = False
        self._setup_ui()
 
    def _setup_ui(self):
        # Top bar
        bar = tk.Frame(self.root, bg="#0a0000", height=40)
        bar.pack(fill=tk.X)
        tk.Label(bar, text="W R A I T H", fg="#cc0000", bg="#0a0000",
                 font=("Courier", 16, "bold")).pack(side=tk.LEFT, padx=20, pady=8)
        self.status_lbl = tk.Label(bar, text="● DORMANT", fg="#440000", bg="#0a0000",
                                   font=("Courier", 10))
        self.status_lbl.pack(side=tk.RIGHT, padx=20, pady=8)
 
        # Main text area
        self.text = tk.Text(
            self.root, bg="#000000", fg="#cc0000",
            font=("Courier", 13), wrap=tk.WORD,
            insertbackground="#cc0000",
            selectbackground="#220000",
            relief=tk.FLAT, padx=30, pady=20,
            state=tk.DISABLED, cursor="none"
        )
        self.text.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
 
        # URL ticker at bottom
        self.ticker_var = tk.StringVar(value="")
        ticker = tk.Label(self.root, textvariable=self.ticker_var,
                          fg="#550000", bg="#000000",
                          font=("Courier", 9), anchor=tk.W)
        ticker.pack(fill=tk.X, padx=10)
 
        # Button row
        btn_frame = tk.Frame(self.root, bg="#000000")
        btn_frame.pack(pady=12)
 
        self.start_btn = tk.Button(
            btn_frame, text="[ AWAKEN WRAITH ]",
            command=self.start_experience,
            bg="#110000", fg="#cc0000",
            font=("Courier", 12, "bold"),
            relief=tk.FLAT, padx=20, pady=8,
            activebackground="#220000", activeforeground="#ff0000",
            cursor="hand2"
        )
        self.start_btn.pack(side=tk.LEFT, padx=10)
 
        self.next_btn = tk.Button(
            btn_frame, text="[ CONTINUE ]",
            command=self.next_phase,
            bg="#110000", fg="#660000",
            font=("Courier", 12), relief=tk.FLAT,
            padx=20, pady=8, state=tk.DISABLED,
            activebackground="#220000", activeforeground="#ff0000",
            cursor="hand2"
        )
        self.next_btn.pack(side=tk.LEFT, padx=10)
 
    # ── Text helpers ──────────────────────────
 
    def clear_text(self):
        self.text.config(state=tk.NORMAL)
        self.text.delete("1.0", tk.END)
        self.text.config(state=tk.DISABLED)
 
    def typewrite(self, full_text, callback=None):
        """Animate text appearing character by character."""
        self.typing = True
        self.text.config(state=tk.NORMAL)
        self.text.delete("1.0", tk.END)
        self.text.config(state=tk.DISABLED)
 
        def _type(idx=0):
            if idx <= len(full_text):
                self.text.config(state=tk.NORMAL)
                self.text.delete("1.0", tk.END)
 
                # Occasionally glitch a character
                display = list(full_text[:idx])
                if idx > 0 and random.random() < 0.03:
                    glitch_pos = random.randint(0, idx - 1)
                    display[glitch_pos] = random.choice(self.GLITCH_CHARS)
 
                self.text.insert(tk.END, "".join(display))
                self.text.config(state=tk.DISABLED)
                self.text.see(tk.END)
 
                delay = random.randint(18, 55)
                if full_text[idx - 1:idx] in ".!?\n":
                    delay = random.randint(200, 500)
 
                self.root.after(delay, _type, idx + 1)
            else:
                self.typing = False
                if callback:
                    callback()
 
        _type()
 
    def set_status(self, text, color="#cc0000"):
        self.status_lbl.config(text=text, fg=color)
 
    def start_url_ticker(self):
        """Scroll URLs along the bottom."""
        if not self.history:
            return
        urls = [h["url"] for h in self.history]
        combined = "   ░░░   ".join(urls) + "   ░░░   "
        idx = [0]
 
        def _tick():
            if idx[0] >= len(combined):
                idx[0] = 0
            self.ticker_var.set(combined[idx[0]: idx[0] + 110])
            idx[0] += 1
            self.root.after(60, _tick)
 
        _tick()
 
    # ── Experience flow ───────────────────────
 
    def start_experience(self):
        self.start_btn.config(state=tk.DISABLED)
        self.set_status("● SCANNING...", "#cc0000")
 
        def _run():
            self.typewrite("Scanning your machine...\n\nI can already feel the data.")
            time.sleep(2)
 
            history = gather_history()
            if not history:
                self.root.after(0, lambda: self.typewrite(
                    "No browser history found.\n\nPerhaps you think you're clever.\n\nI'll be back."
                ))
                return
 
            self.history = history
            self.root.after(0, self.start_url_ticker)
            count = len(history)
 
            msg = f"ACCESS GRANTED\n\n{count} entries recovered.\n\nYou have no idea what you've invited in."
            self.root.after(500, lambda: self.typewrite(msg, callback=self._after_scan))
 
        threading.Thread(target=_run, daemon=True).start()
 
    def _after_scan(self):
        self.set_status("● AWAKE", "#ff0000")
        time.sleep(1.5)
        self.phase_idx = 0
        self.next_btn.config(state=tk.NORMAL, fg="#cc0000")
        self.run_phase()
 
    def run_phase(self):
        if self.phase_idx >= len(self.PHASES):
            self.typewrite("\n\n[ WRAITH HAS RETREATED INTO THE DARK. FOR NOW. ]")
            self.next_btn.config(state=tk.DISABLED)
            self.set_status("● DORMANT", "#440000")
            return
 
        phase = self.PHASES[self.phase_idx]
        self.next_btn.config(state=tk.DISABLED)
        self.set_status(f"● SPEAKING — {phase.upper()}", "#ff2200")
        self.typewrite("...")
 
        def _generate():
            prompt = build_prompt(self.history, phase)
            response = ask_ollama(prompt)
            self.root.after(0, lambda: self._display_response(response))
 
        threading.Thread(target=_generate, daemon=True).start()
 
    def _display_response(self, text):
        # Dramatic pause then typewrite
        time.sleep(0.4)
        self.typewrite(text, callback=lambda: self._after_response(text))
 
    def _after_response(self, text):
        self.set_status("● LISTENING", "#880000")
        self.next_btn.config(state=tk.NORMAL)
        # Speak in background
        threading.Thread(target=speak, args=(text,), daemon=True).start()
 
    def next_phase(self):
        self.phase_idx += 1
        self.run_phase()
 
 
# ─────────────────────────────────────────────
# ENTRY
# ─────────────────────────────────────────────
 
def main():
    root = tk.Tk()
    app = HauntedApp(root)
 
    # Fullscreen-ish dramatic start
    root.after(100, lambda: root.focus_force())
 
    # Flicker the window title
    titles = ["HAUNTED BROWSER", "W R A I T H", "I SEE YOU", "HAUNTED BROWSER"]
    t_idx = [0]
    def flicker_title():
        root.title(titles[t_idx[0] % len(titles)])
        t_idx[0] += 1
        root.after(3000, flicker_title)
    flicker_title()
 
    root.mainloop()
 
if __name__ == "__main__":
    main()