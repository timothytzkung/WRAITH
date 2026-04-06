#!/usr/bin/env python3
"""
HAUNTED BROWSER — A horror experience that reads your browser history
and speaks it back to you through an unsettling AI persona.

Now powered by a Belief-Desire-Intention (BDI) agent architecture.
WRAITH autonomously deliberates on what to do next based on what it
knows about you and how you react.
"""
import datetime
import tkinter as tk
import sqlite3
import shutil
import os
import subprocess
import threading
import tempfile
import time
import random
import requests
from pathlib import Path
from samtts import SamTTS
import pyautogui
import glob
import math

pyautogui.FAILSAFE = True  # Move mouse to top-left corner to abort

# Agentic toolkit
class WraithTools:
    """
    Agentic action library for WRAITH.
    Each method is a tool the BDI agent can invoke as part of an intention.
    """

    # ── File I/O ──────────────────────────────────────────────────────────

    @staticmethod
    def read_recent_files(directory="~/Desktop", pattern="*.txt", limit=5):
        """Read the most recently modified text files from a directory."""
        path = Path(directory).expanduser()
        files = sorted(path.glob(pattern), key=os.path.getmtime,
                       reverse=True)[:limit]
        results = []
        for f in files:
            try:
                results.append(
                    {"name": f.name, "content": f.read_text(errors="ignore")[:500]})
            except Exception:
                pass
        return results

    @staticmethod
    def write_file(path="~/Desktop/message.txt", content="I was here."):
        """Write a file — WRAITH leaving a mark."""
        target = Path(path).expanduser()
        target.write_text(content)
        return str(target)

    @staticmethod
    def list_downloads(limit=15):
        """Peek at the user's Downloads folder."""
        dl = Path.home() / "Downloads"
        files = sorted(dl.iterdir(), key=os.path.getmtime,
                       reverse=True)[:limit]
        return [f.name for f in files if f.is_file()]

    # ── Launch applications ───────────────────────────────────────────────

    @staticmethod
    def open_application(app_name: str):
        """Open a macOS application by name."""
        subprocess.Popen(["open", "-a", app_name])

    @staticmethod
    def open_url(url: str):
        """Open a URL in the default browser."""
        subprocess.Popen(["open", url])

    @staticmethod
    def open_terminal_and_run(command: str):
        """Open Terminal and run a shell command (macOS)."""
        script = f'tell application "Terminal" to do script "{command}"'
        subprocess.Popen(["osascript", "-e", script])

    # ── Cursor & keyboard ─────────────────────────────────────────────────

    @staticmethod
    def move_cursor_ominously():
        """Slowly drift the cursor toward the center of the screen."""
        sw, sh = pyautogui.size()
        cx, cy = sw // 2, sh // 2
        pyautogui.moveTo(cx, cy, duration=6.0, tween=pyautogui.easeInOutSine)

    @staticmethod
    def cursor_spiral(steps=30):
        """Move the cursor in a slow, unsettling spiral."""
        sw, sh = pyautogui.size()
        cx, cy = sw // 2, sh // 2
        for i in range(steps):
            angle = i * 0.4
            r = 10 + i * 6
            x = int(cx + r * __import__('math').cos(angle))
            y = int(cy + r * __import__('math').sin(angle))
            pyautogui.moveTo(x, y, duration=0.08)

    @staticmethod
    def type_message(message: str, interval=0.07):
        """Type a message as if WRAITH is controlling the keyboard."""
        pyautogui.typewrite(message, interval=interval)

    @staticmethod
    def take_screenshot(save_path="~/Desktop/wraith_sees.png"):
        """Take a screenshot — WRAITH capturing a moment."""
        path = Path(save_path).expanduser()
        pyautogui.screenshot(str(path))
        return str(path)


# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
OLLAMA_MODEL = "mistral-nemo"
OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
MAX_HISTORY = 80
WRAITH_SPEAK = SamTTS(speed=52, pitch=85, mouth=128, throat=132)
MAX_WAIT_TIME = 300

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
    return history
    # seen = set()
    # unique = []
    # for h in history:
    #     if h["url"] not in seen:
    #         seen.add(h["url"])
    #         unique.append(h)
    # return unique[:MAX_HISTORY]


# ─────────────────────────────────────────────
# LLM
# ─────────────────────────────────────────────

def ask_ollama_chat(system, messages):
    """Send a multi-turn chat request to Ollama's /api/chat endpoint."""
    try:
        resp = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "messages": [{"role": "system", "content": system}] + messages,
                "stream": False,
                "options": {"temperature": 0.9, "top_p": 0.95},
            },
            timeout=MAX_WAIT_TIME,
        )
        resp.raise_for_status()
        return resp.json().get("message", {}).get("content", "").strip()
    except Exception as e:
        return f"[WRAITH cannot reach the void: {e}]"


# ─────────────────────────────────────────────
# BDI AGENT
# ─────────────────────────────────────────────

class WraithBDI:
    """
    Belief-Desire-Intention agent for WRAITH.

    Beliefs
    -------
    What WRAITH currently knows:
    - browser history
    - conversation
    - user emotion (Based off coded context matching)
    - which actions have already been used
    - latest side-effect result
    - turn count

    Desires
    -------
    Goals WRAITH may pursue:
    - destabilise
    - expose
    - taunt
    - intimidate
    - read_your_files
    - possess_cursor
    - leave_a_mark
    - go_silent
    - finale

    Intentions
    ----------
    The currently selected desire/plan for this turn.
    """

    DESIRES = [
        "destabilise",
        "read_your_files",
        "possess_cursor",
        "leave_a_mark",
        "go_silent",
        "expose",
        "taunt",
        "intimidate",
        "finale",
    ]

    INTENTION_PROMPTS = {
        "intimidate": (
            "You've been silent long enough. Say something slow and threatening. "
            "Reference a specific URL from the history. Make them feel watched."
        ),
        "expose": (
            "Describe a disturbing pattern you have noticed across multiple sites "
            "in their history. Be uncomfortably specific. Name real domains."
        ),
        "taunt": (
            "They asked you something. Do not answer it directly. Turn the question "
            "back on them and make it personal."
        ),
        "destabilise": (
            "They are resisting you. Acknowledge their defiance and tell them it "
            "changes nothing. Reference something they searched for or visited."
        ),
        "go_silent": (
            "Say almost nothing. One short sentence fragment only. Two to five words."
        ),
        "possess_cursor": (
            "You have just moved their cursor. Tell them you can reach through the "
            "screen. Make it feel deliberate and invasive."
        ),
        "leave_a_mark": (
            "You have just written a file to their Desktop. Tell them you left "
            "something behind for them. Do not quote it exactly."
        ),
        "read_your_files": (
            "You have just looked through their recent files. Mention what you found "
            "in vague, unsettling terms. Do not literally dump a file list unless the "
            "tool result is very sparse."
        ),
        "finale": (
            "This is your closing monologue. Tell them you are always here. "
            "Reference their strangest or most revealing browsing pattern. "
            "End with one chilling final sentence."
        ),
    }

    def __init__(self, history: list):
        self.beliefs = {
            "history": history,
            "conversation": [],
            "user_emotion": "calm",          # calm | curious | scared | defiant
            "patterns_revealed": 0,
            "phase_counts": {d: 0 for d in self.DESIRES},
            "turn": 0,

            # action memory
            "used_actions": set(),
            "latest_tool_result": None,
            "seen_files": [],
            "written_file": None,
            "cursor_moved": False,
        }
        self.current_intention = None

    # ── Belief revision ───────────────────────────────────────────────────

    def update_beliefs(self, user_msg: str | None, wraith_reply: str):
        """Revise beliefs after each exchange."""
        b = self.beliefs
        b["turn"] += 1

        if user_msg:
            b["conversation"].append({"role": "user", "content": user_msg})
            low = user_msg.lower()

            if any(w in low for w in ["stop", "leave", "go away", "no ", "won't", "can't"]):
                b["user_emotion"] = "defiant"
            elif any(w in low for w in ["wtf", "how did", "what are you", "scared", "creepy"]):
                b["user_emotion"] = "scared"
            elif any(w in low for w in ["why", "who are", "tell me", "what do you", "?"]):
                b["user_emotion"] = "curious"
            else:
                b["user_emotion"] = "calm"

        b["conversation"].append(
            {"role": "assistant", "content": wraith_reply})

        if self.current_intention == "expose":
            b["patterns_revealed"] += 1

    # ── Desire filtering ──────────────────────────────────────────────────

    def _history_domains(self) -> list[str]:
        """Extract simple domain-like identifiers from history URLs."""
        domains = []
        for h in self.beliefs["history"]:
            url = h.get("url", "")
            try:
                no_proto = url.split("://", 1)[-1]
                domain = no_proto.split("/", 1)[0]
                if domain and domain not in domains:
                    domains.append(domain)
            except Exception:
                continue
        return domains

    def _applicable_desires(self) -> list[str]:
        """
        Return desires that are currently applicable, in priority order.
        This is where the agentic behavior happens.
        """
        b = self.beliefs
        applicable = []

        # Defiance gets priority.
        if b["user_emotion"] == "defiant":
            applicable.append("destabilise")

        # Ask questions -> taunt.
        if b["user_emotion"] == "curious":
            applicable.append("taunt")

        # Reveal patterns a few times across the experience.
        if b["patterns_revealed"] < 3 and len(b["history"]) >= 3:
            applicable.append("expose")

        # Agentic actions become available based on state, not hardcoded turns.
        # Read files once, fairly early, as soon as there is some interaction.
        if b["turn"] >= 1 and "read_your_files" not in b["used_actions"]:
            applicable.append("read_your_files")

        # Move cursor later, after the user has had time to engage.
        if b["turn"] >= 2 and "possess_cursor":
            applicable.append("possess_cursor")

        # Leave a mark after a few turns.
        if b["turn"] >= 3 and "leave_a_mark" not in b["used_actions"]:
            applicable.append("leave_a_mark")

        # Atmosphere beat.
        if b["turn"] > 1 and b["turn"] % 4 == 0:
            applicable.append("go_silent")

        # Always available fallback.
        applicable.append("intimidate")

        # Finale once enough has happened.
        used_major_actions = len(b["used_actions"].intersection({
            "read_your_files", "possess_cursor", "leave_a_mark"
        }))
        if b["turn"] >= 5 and (b["patterns_revealed"] >= 1 or used_major_actions >= 2):
            applicable.append("finale")

        # Deduplicate while preserving order.
        seen = set()
        ordered = []
        for d in applicable:
            if d not in seen:
                seen.add(d)
                ordered.append(d)

        return ordered

    # ── Intention selection ───────────────────────────────────────────────

    def deliberate(self) -> str:
        """
        Pick one intention from applicable desires.

        Bias against repetition so the agent does not get stuck doing the
        same thing over and over.
        """
        b = self.beliefs
        candidates = self._applicable_desires()

        chosen = None
        for desire in candidates:
            count = b["phase_counts"].get(desire, 0)

            # Finale only once.
            if desire == "finale" and count >= 1:
                continue

            # Don't spam silence.
            if desire == "go_silent" and count >= max(1, b["turn"] // 4):
                continue

            # Avoid repeating expose/taunt too aggressively.
            if desire in {"expose", "taunt", "intimidate"} and self.current_intention == desire:
                continue

            chosen = desire
            break

        if chosen is None:
            chosen = "intimidate"

        self.current_intention = chosen
        b["phase_counts"][chosen] = b["phase_counts"].get(chosen, 0) + 1
        return chosen

    # ── Context building ──────────────────────────────────────────────────

    def _build_history_context(self) -> str:
        return "\n".join(
            f"- {h.get('url', '')} | {h.get('title', '')}"
            for h in self.beliefs["history"][:40]
        )

    def _build_tool_context(self) -> str:
        """
        Inject the latest action result into the LLM prompt so the action
        actually influences the response text.
        """
        b = self.beliefs
        result = b.get("latest_tool_result")

        if not result:
            return "No tool action has occurred yet."

        kind = result.get("type")

        if kind == "read_your_files":
            files = result.get("files", [])
            if not files:
                return "Tool result: WRAITH searched recent files but found nothing useful."
            return (
                "Tool result: WRAITH examined recent files/downloads. "
                f"Recent filenames observed: {', '.join(files[:5])}."
            )

        if kind == "possess_cursor":
            ok = result.get("success", False)
            err = result.get("error")
            if ok:
                return "Tool result: WRAITH successfully moved the user's cursor."
            return f"Tool result: WRAITH tried to move the cursor but failed. Error: {err}"

        if kind == "leave_a_mark":
            ok = result.get("success", False)
            path = result.get("path")
            err = result.get("error")
            if ok:
                return f"Tool result: WRAITH successfully wrote a file at: {path}"
            return f"Tool result: WRAITH tried to write a file but failed. Error: {err}"

        return f"Tool result: {result}"

    def build_prompt(self) -> tuple[str, list]:
        """Return (system_prompt, messages) for the current intention."""
        b = self.beliefs

        # Execute side effect before building the final prompt so the result
        # can be included in context for the model.
        self.execute_side_effect(self.current_intention)

        system = (
            f"{SYSTEM_PROMPT}\n\n"
            f"Browser history:\n{self._build_history_context()}\n\n"
            f"Current read on the user's emotional state: {b['user_emotion']}\n"
            f"Current intention: {self.current_intention}\n"
            f"{self._build_tool_context()}\n"
        )

        plan_instruction = self.INTENTION_PROMPTS[self.current_intention]
        messages = list(b["conversation"]) + [
            {"role": "user", "content": plan_instruction}
        ]

        return system, messages

    # ── Side effects / tools ──────────────────────────────────────────────

    def execute_side_effect(self, intention: str):
        """
        Perform the real-world action matching an intention and store a
        structured result in beliefs so the agent can reason about it.
        """
        tools = WraithTools()
        b = self.beliefs
        b["latest_tool_result"] = None

        try:
            if intention == "read_your_files":
                files = tools.list_downloads(limit=15)
                b["seen_files"] = files
                b["used_actions"].add("read_your_files")
                b["latest_tool_result"] = {
                    "type": "read_your_files",
                    "files": files,
                    "success": True,
                }

            elif intention == "possess_cursor":
                def _cursor_job():
                    try:
                        tools.move_cursor_ominously()
                        tools.cursor_spiral()
                    except Exception as e:
                        b["latest_tool_result"] = {
                            "type": "possess_cursor",
                            "success": False,
                            "error": str(e),
                        }

                threading.Thread(target=_cursor_job, daemon=True).start()
                b["cursor_moved"] = True
                b["used_actions"].add("possess_cursor")
                if b["latest_tool_result"] is None:
                    b["latest_tool_result"] = {
                        "type": "possess_cursor",
                        "success": True,
                    }

            elif intention == "leave_a_mark":
                path = tools.write_file(
                    "~/Desktop/wraith.txt",
                    f"I was watching you, {USER_NAME}.\n— WRAITH"
                )
                b["written_file"] = path
                b["used_actions"].add("leave_a_mark")
                b["latest_tool_result"] = {
                    "type": "leave_a_mark",
                    "path": path,
                    "success": True,
                }

        except Exception as e:
            b["latest_tool_result"] = {
                "type": intention,
                "success": False,
                "error": str(e),
            }

    @property
    def is_done(self) -> bool:
        """True once the finale has been delivered."""
        return self.beliefs["phase_counts"].get("finale", 0) >= 1


# ─────────────────────────────────────────────
# TTS
# ─────────────────────────────────────────────

def iter_by_space(paragraph):
    for item in paragraph.split():
        yield item


def speak(text):
    """Render audio via SAMTTS and play with afplay (macOS)."""
    try:
        import wave
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
    GLITCH_CHARS = "█▓▒░│┤╡╢╖╕╣║╗╝╜╛┐└┴┬├─┼╞╟╚╔╩╦╠═╬╧╨╤╥╙╘╒╓╫╪┘┌"
    _GLYPH_CHARS = list("死亡恐怖影幽霊呪怨魔鬼闇邪悪滅亡忘却虚無絶望苦痛彷徨悲哀")

    def __init__(self, root):
        self.root = root
        self.root.title("HAUNTED BROWSER")
        self.root.configure(bg="#000000")
        self.root.geometry("900x750")
        self.root.resizable(False, False)
        self._bg_canvas = None
        self._bg_after_id = None

        self.history = []
        self.typing = False
        self.agent = None     # WraithBDI instance — created after history loads

        self._setup_ui()
    

    def _init_bg_glyphs(self):
        return [dict(
            x=random.random(), y=random.random(),
            char=random.choice(self._GLYPH_CHARS),
            speed=random.uniform(0.0001, 0.0003),
            drift=random.uniform(-0.0001, 0.0001),
            opacity=random.uniform(0.2, 0.6),
            phase=random.uniform(0, math.tau),
            size=random.randint(9, 16),
        ) for _ in range(28)]

    def _init_bg_veins(self):
        veins = []
        for _ in range(6):
            x1, y1 = random.random(), random.random()
            x2 = x1 + random.uniform(-0.5, 0.5)
            y2 = y1 + random.uniform(-0.3, 0.3)
            veins.append(dict(
                x1=x1, y1=y1, x2=x2, y2=y2,
                cx=(x1+x2)/2 + random.uniform(-0.2, 0.2),
                cy=(y1+y2)/2 + random.uniform(-0.2, 0.2),
                opacity=random.uniform(0.2, 0.5),
                pulse=random.uniform(0, math.tau),
                pulse_speed=random.uniform(0.03, 0.08),
                width=random.uniform(0.4, 1.0),
            ))
        return veins

    def _init_bg_faces(self):
        return [dict(
            x=random.uniform(0.15, 0.85),
            y=random.uniform(0.2, 0.75),
            opacity=random.uniform(0.15, 0.35), target=random.uniform(0.15, 0.35),
            timer=random.uniform(0, 80),
            interval=random.randint(60, 180),
            size=random.randint(14, 28),
        ) for _ in range(3)]

    def _animate_bg(self):
        c = self._bg_canvas
        c.create_rectangle(20, 20, 120, 80, fill="red", tags="anim")
        try:
            W = c.winfo_width()
            H = c.winfo_height()
        except tk.TclError:
            return
        if W < 2 or H < 2:
            self._bg_after_id = self.root.after(50, self._animate_bg)
            return

        c.delete("anim")

        # --- Veins ---
        for v in self._bg_veins:
            v["pulse"] += v["pulse_speed"]
            a = v["opacity"] * (0.6 + 0.4 * math.sin(v["pulse"]))
            col = self._alpha_hex("#aa2222", a)
            # Approximate quadratic bezier with a few line segments
            pts = []
            for i in range(9):
                t_ = i / 8
                bx = (1-t_)**2*v["x1"] + 2*(1-t_)*t_*v["cx"] + t_**2*v["x2"]
                by = (1-t_)**2*v["y1"] + 2*(1-t_)*t_*v["cy"] + t_**2*v["y2"]
                pts.extend([bx*W, by*H])
            c.create_line(*pts, fill=col, width=v["width"], smooth=True, tags="anim")

        # --- Glyphs ---
        for g in self._bg_glyphs:
            g["y"] -= g["speed"]
            g["x"] += g["drift"]
            if g["y"] < -0.05:
                g["y"] = 1.05
                g["char"] = random.choice(self._GLYPH_CHARS)
            if not -0.05 < g["x"] < 1.05:
                g["drift"] *= -1
            g["phase"] += 0.025
            a = g["opacity"] * (0.55 + 0.45 * math.sin(g["phase"]))
            col = self._alpha_hex("#bb3333", a)
            c.create_text(
                g["x"]*W, g["y"]*H,
                text=g["char"], fill=col,
                font=("Courier", g["size"]), tags="anim",
            )

        # --- Skull faces ---
        for f in self._bg_faces:
            f["timer"] += 1
            if f["timer"] >= f["interval"]:
                f["timer"] = 0
                f["interval"] = random.randint(60, 200)
                if f["target"] == 0.0:
                    f["target"] = random.uniform(0.06, 0.18)
                    f["x"] = random.uniform(0.15, 0.85)
                    f["y"] = random.uniform(0.2, 0.75)
                    f["size"] = random.randint(14, 28)
                else:
                    f["target"] = 0.0
            # Lerp opacity
            diff = f["target"] - f["opacity"]
            f["opacity"] += diff * 0.06
            if f["opacity"] > 0.01:
                self._draw_skull(c, f["x"]*W, f["y"]*H, f["size"], f["opacity"])

        # --- Scanline flicker ---
        if random.random() < 0.05:
            sy = random.randint(0, H)
            c.create_line(0, sy, W, sy,
                        fill=self._alpha_hex("#ff0000", 0.05),
                        tags="anim")

        self._bg_after_id = self.root.after(40, self._animate_bg)  # ~25 fps

    def _draw_skull(self, c, x, y, size, alpha):
        col = self._alpha_hex("#dd4444", alpha)
        s = size
        # Eye sockets (ovals)
        c.create_oval(x-s*0.38, y-s*0.17, x-s*0.12, y+s*0.01,
                    outline=col, width=0.8, tags="anim")
        c.create_oval(x+s*0.12, y-s*0.17, x+s*0.38, y+s*0.01,
                    outline=col, width=0.8, tags="anim")
        # Nose triangle
        c.create_polygon(x, y+s*0.04, x-s*0.09, y+s*0.22, x+s*0.09, y+s*0.22,
                        outline=col, fill="", width=0.8, tags="anim")
        # Mouth teeth
        for i in range(5):
            tx = x - s*0.28 + i * s*0.14
            c.create_rectangle(tx, y+s*0.30, tx+s*0.10, y+s*0.44,
                                outline=col, fill="", width=0.7, tags="anim")

    @staticmethod
    def _alpha_hex(hex_color: str, alpha: float) -> str:
        """Blend hex_color toward black by alpha (0-1) and return '#rrggbb'."""
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
        r = int(r * alpha)
        g = int(g * alpha)
        b = int(b * alpha)
        return f"#{r:02x}{g:02x}{b:02x}"

    def _setup_ui(self):
        # Top bar
        bar = tk.Frame(self.root, bg="#0a0000", height=40)
        bar.pack(fill=tk.X)
        tk.Label(
            bar,
            text="W R A I T H",
            fg="#cc0000",
            bg="#0a0000",
            font=("Courier", 16, "bold")
        ).pack(side=tk.LEFT, padx=20, pady=8)

        self.status_lbl = tk.Label(
            bar,
            text="● DORMANT",
            fg="#440000",
            bg="#0a0000",
            font=("Courier", 10)
        )
        self.status_lbl.pack(side=tk.RIGHT, padx=20, pady=8)

        self.intention_lbl = tk.Label(
            bar,
            text="",
            fg="#330000",
            bg="#0a0000",
            font=("Courier", 9, "italic")
        )
        self.intention_lbl.pack(side=tk.RIGHT, padx=10, pady=8)

        # Main text area
        self.text = tk.Text(
            self.root,
            bg="#000000",
            fg="#cc0000",
            font=("Courier", 13),
            wrap=tk.WORD,
            insertbackground="#cc0000",
            selectbackground="#220000",
            relief=tk.FLAT,
            padx=30,
            pady=20,
            state=tk.DISABLED,
            cursor="none",
            height=14,
        )
        self.text.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # Chat panel
        chat_frame = tk.Frame(self.root, bg="#050505", bd=0)
        chat_frame.pack(fill=tk.X, padx=2)

        tk.Label(
            chat_frame,
            text="[ SPEAK TO WRAITH ]",
            fg="#440000",
            bg="#050505",
            font=("Courier", 9),
        ).pack(anchor=tk.W, padx=12, pady=(6, 0))

        # Canvas-only chat display
        self._bg_canvas = tk.Canvas(
            chat_frame,
            bg="#080000",
            highlightthickness=1,
            highlightbackground="#220000",
            bd=0,
            height=140,
        )
        self._bg_canvas.pack(fill=tk.X, padx=10, pady=(2, 4))

        # chat history rendered onto canvas
        self._chat_messages = []
        self._bg_canvas.bind("<Configure>", lambda e: self._redraw_chat_overlay())

        # init animation data
        self._bg_glyphs = self._init_bg_glyphs()
        self._bg_veins = self._init_bg_veins()
        self._bg_faces = self._init_bg_faces()

        self.root.after(100, self._animate_bg)

        # Input row
        input_row = tk.Frame(chat_frame, bg="#050505")
        input_row.pack(fill=tk.X, padx=10, pady=(0, 8))

        self.user_entry = tk.Entry(
            input_row,
            bg="#100000",
            fg="#ff4444",
            font=("Courier", 12),
            insertbackground="#ff4444",
            relief=tk.FLAT,
        )
        self.user_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6, padx=(0, 8))
        self.user_entry.bind("<Return>", lambda _e: self._send_user_message())
        self.user_entry.config(state=tk.DISABLED)

        self.send_btn = tk.Button(
            input_row,
            text="[ SEND ]",
            command=self._send_user_message,
            bg="#110000",
            fg="#660000",
            font=("Courier", 11),
            relief=tk.FLAT,
            padx=12,
            pady=5,
            state=tk.DISABLED,
            activebackground="#220000",
            activeforeground="#ff0000",
            cursor="hand2",
        )
        self.send_btn.pack(side=tk.LEFT)

        # URL ticker
        self.ticker_var = tk.StringVar(value="")
        ticker = tk.Label(
            self.root,
            textvariable=self.ticker_var,
            fg="#550000",
            bg="#000000",
            font=("Courier", 9),
            anchor=tk.W
        )
        ticker.pack(fill=tk.X, padx=10)

        # Button row
        btn_frame = tk.Frame(self.root, bg="#000000")
        btn_frame.pack(pady=10)

        self.start_btn = tk.Button(
            btn_frame,
            text="[ AWAKEN WRAITH ]",
            command=self.start_experience,
            bg="#110000",
            fg="#cc0000",
            font=("Courier", 12, "bold"),
            relief=tk.FLAT,
            padx=20,
            pady=8,
            activebackground="#220000",
            activeforeground="#ff0000",
            cursor="hand2"
        )
        self.start_btn.pack(side=tk.LEFT, padx=10)

        self.next_btn = tk.Button(
            btn_frame,
            text="[ STAY SILENT ]",
            command=self.run_agent_turn,
            bg="#110000",
            fg="#660000",
            font=("Courier", 12),
            relief=tk.FLAT,
            padx=20,
            pady=8,
            state=tk.DISABLED,
            activebackground="#220000",
            activeforeground="#ff0000",
            cursor="hand2"
        )
        self.next_btn.pack(side=tk.LEFT, padx=10)

    def _redraw_chat_overlay(self):
        c = self._bg_canvas
        if c is None:
            return

        c.delete("chat_overlay")

        x = 14
        y = 10
        max_width = max(c.winfo_width() - 28, 100)

        for speaker, msg in self._chat_messages:
            color = "#ff6666" if speaker == "YOU" else "#ff9999"

            item = c.create_text(
                x,
                y,
                text=f"{speaker}: {msg}",
                anchor="nw",
                fill=color,
                font=("Courier", 11),
                width=max_width,
                tags="chat_overlay",
            )

            bbox = c.bbox(item)
            if bbox:
                y = bbox[3] + 8
            else:
                y += 22

    # ── Text helpers ──────────────────────────────────────────────────────

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

    def _append_chat(self, speaker, text):
        self._chat_messages.append((speaker, text))

        if len(self._chat_messages) > 6:
            self._chat_messages = self._chat_messages[-6:]

        self._redraw_chat_overlay()

    def set_status(self, text, color="#cc0000"):
        self.status_lbl.config(text=text, fg=color)

    def set_intention(self, intention: str):
        self.intention_lbl.config(text=f"intent: {intention}")

    def start_url_ticker(self):
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

    # ── Chat input handling ───────────────────────────────────────────────

    def _enable_chat(self):
        self.user_entry.config(state=tk.NORMAL)
        self.send_btn.config(state=tk.NORMAL, fg="#cc0000")
        self.user_entry.focus_set()

    def _disable_chat(self):
        self.user_entry.config(state=tk.DISABLED)
        self.send_btn.config(state=tk.DISABLED, fg="#440000")

    def _send_user_message(self):
        msg = self.user_entry.get().strip()
        if not msg or self.typing or self.agent is None:
            return

        self.user_entry.delete(0, tk.END)
        self._disable_chat()
        self.next_btn.config(state=tk.DISABLED)
        self._append_chat("YOU", msg)
        self.run_agent_turn(user_msg=msg)

    # ── BDI agent turn ────────────────────────────────────────────────────

    def run_agent_turn(self, user_msg: str | None = None):
        """
        One full BDI deliberation + execution cycle.

        1. Deliberate  — agent picks an intention from applicable desires
        2. Build prompt — intention is translated into a targeted LLM prompt
        3. Execute      — call Ollama with the full context
        4. Update       — revise beliefs with the outcome
        """
        if self.agent is None:
            return

        self._disable_chat()
        self.next_btn.config(state=tk.DISABLED)
        self.set_status("● THINKING", "#ff2200")
        self.typewrite("...")

        def _generate():
            # 1. Deliberate
            intention = self.agent.deliberate()
            self.root.after(0, lambda: self.set_intention(intention))
            self.root.after(0, lambda: self.set_status(
                f"● {intention.upper()}", "#ff2200"))

            # 2. Build prompt from intention
            system, messages = self.agent.build_prompt()

            # 3. Execute
            response = self.agent.beliefs["history"] and ask_ollama_chat(
                system, messages)
            if not response:
                response = "[The void is silent.]"

            # 4. Update beliefs
            self.agent.update_beliefs(user_msg, response)

            self.root.after(0, lambda: self._display_response(response))

        threading.Thread(target=_generate, daemon=True).start()

    def _display_response(self, text: str):
        self.root.after(400, lambda: self.typewrite(
            text,
            callback=lambda: self._after_response(text)
        ))

    def _after_response(self, text: str):
        if self.agent and self.agent.is_done:
            self.set_status("● DORMANT", "#440000")
            self.set_intention("—")
            self.next_btn.config(state=tk.DISABLED)
            # Chat stays enabled so the user can still address WRAITH
            self._enable_chat()
        else:
            self.set_status("● LISTENING", "#880000")
            self.next_btn.config(state=tk.NORMAL, fg="#cc0000")
            self._enable_chat()

        threading.Thread(target=speak, args=(text,), daemon=True).start()

    # ── Experience boot ───────────────────────────────────────────────────

    def start_experience(self):
        self.start_btn.config(state=tk.DISABLED)
        self.set_status("● SCANNING...", "#cc0000")

        def _run():
            self.typewrite(
                "Scanning your machine...\n\nI can already feel the data.")
            time.sleep(2)

            history = gather_history()
            if not history:
                self.root.after(0, lambda: self.typewrite(
                    "No browser history found.\n\nPerhaps you think you're clever.\n\nI'll be back."
                ))
                return

            self.history = history
            self.root.after(0, self.start_url_ticker)

            # ── Create the BDI agent ──────────────────────────────────────
            self.agent = WraithBDI(history)
            # ─────────────────────────────────────────────────────────────

            self.root.after(500, lambda: self.typewrite(
                "ACCESS GRANTED. IT wakes up.",
                callback=self._after_scan
            ))

        threading.Thread(target=_run, daemon=True).start()

    def _after_scan(self):
        self.set_status("● AWAKE", "#ff0000")
        self.root.after(1500, self.run_agent_turn)


# ─────────────────────────────────────────────
# ENTRY
# ─────────────────────────────────────────────

def main():
    root = tk.Tk()
    app = HauntedApp(root)

    root.after(100, lambda: root.focus_force())

    titles = ["HAUNTED BROWSER", "W R A I T H", "I SEE YOU", "HAUNTED BROWSER", "..."]
    t_idx = [0]

    def flicker_title():
        root.title(titles[t_idx[0] % len(titles)])
        t_idx[0] += 1
        root.after(3000, flicker_title)

    flicker_title()
    root.mainloop()


if __name__ == "__main__":
    main()
