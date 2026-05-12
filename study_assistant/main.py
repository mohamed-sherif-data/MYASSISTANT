# main.py
"""
مساعد المذاكرة v8.0 — هيكلة جديدة بالكامل.
نقطة الدخول الوحيدة. نظيفة، بدون استيرادات دائرية.
"""

import ctypes
import logging
import threading  # FIX: كان مفقوداً
import sys
import tkinter as tk
from pathlib import Path

# ── core ──────────────────────────────────────────────────────────────────
from core.database import Database
from core.session import SessionManager
from core.pomodoro import PomodoroTimer
from core.gamification import XPManager, DailyChallengeManager

# ── services ──────────────────────────────────────────────────────────────
from services.sound import SoundManager
from services.tts import TTSManager, HAS_TTS
from services.groq_client import GroqClient, GROQ_MODELS
from services.translator import TranslationManager
from services.pdf_manager import PDFManager
from services.youtube import YouTubeSummarizer, HAS_YT

# ── ui ────────────────────────────────────────────────────────────────────
from ui.dashboard import Dashboard

# ── إعدادات أولية ────────────────────────────────────────────────────────
logging.basicConfig(
    filename="study_assistant.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    encoding="utf-8",
)
logger = logging.getLogger(__name__)

NOTES_DIR = Path(__file__).parent / "StudyNotes"
NOTES_DIR.mkdir(exist_ok=True)

# ════════════════════════════════════════════════════════════════════════════
class StudyAssistant:
    """ينشئ كل المكونات ويربطها ويشغل التطبيق."""

    def __init__(self) -> None:
        logger.info("Study Assistant v8.0 starting...")

        # ── قاعدة البيانات ────────────────────────────────────────────────
        self.db = Database()

        # ── الصوت ─────────────────────────────────────────────────────────
        self.sound = SoundManager()

        # ── الجلسة والبومودورو ────────────────────────────────────────────
        self.session = SessionManager(self.db)
        self.pomodoro = PomodoroTimer(
            self.db,
            on_tick=self._on_pomo_tick,
            on_phase=self._on_pomo_phase,
        )

        # ─ـ XP والتحديات ─────────────────────────────────────────────────
        self.xp = XPManager(self.db)
        self.challenge = DailyChallengeManager(self.db, self.xp)

        # ── Groq ──────────────────────────────────────────────────────────
        self.groq = GroqClient(self.db)

        # ── TTS ───────────────────────────────────────────────────────────
        self.tts = TTSManager()

        # ── الترجمة ───────────────────────────────────────────────────────
        self.translator = TranslationManager(
            self.db, self.groq, self.tts, self.sound,
            get_subject=lambda: self.session.subject or "",
        )

        # ─ـ PDF ───────────────────────────────────────────────────────────
        self.pdf = PDFManager(NOTES_DIR, sound=self.sound)

        # ─ـ YouTube ───────────────────────────────────────────────────────
        self.youtube = YouTubeSummarizer(self.db, self.groq, self.pdf)

        # ─ـ ربط observer ────────────────────────────────────────────────
        self.db.on_word_saved(lambda total: [
            self.xp.on_word_saved(total),
            self.challenge.update("save"),
        ])

        # ─ـ Root window مخفية ─────────────────────────────────────────────
        self.root = tk.Tk()
        self.root.withdraw()

        # ─ـ تمرير root للترجمة لعرض Toast ───────────────────────────────
        self.translator.set_toast_callback(self._show_toast)

        # ─ـ UI الرئيسية ──────────────────────────────────────────────────
        self.dashboard = Dashboard(self)

        # ─ـ اختصارات لوحة المفاتيح ──────────────────────────────────────
        self._setup_hotkeys()

        # ─ـ استعادة مسار PDF ────────────────────────────────────────────
        if self.session.active:
            self.pdf.set_lecture(self.session.subject, self.session.lecture)

        # ─ـ أيقونة شريط المهام ───────────────────────────────────────────
        self._setup_tray()

        logger.info("Ready ✅")

    # ── Pomodoro callbacks ────────────────────────────────────────────────
    def _on_pomo_tick(self, remaining: int, phase: str) -> None:
        self._update_tray()

    def _on_pomo_phase(self, phase: str, cycles: int) -> None:
        # FIX: كان phase == "break" وهو غير موجود في PHASE_LABELS
        # الأوجه الصحيحة: "work", "short_break", "long_break"
        if phase in ("short_break", "long_break"):
            self.challenge.update("pomodoro")
            # ملخص PDF عند الانتقال لاستراحة والجلسة نشطة
            if self.session.active:
                self.pdf.add_summary(
                    self.session.subject or "عام",
                    self.session.lecture,
                    cycles,
                    self.pomodoro.work_minutes,
                )

    # ─ـ Hotkeys ───────────────────────────────────────────────────────────
    def _setup_hotkeys(self) -> None:
        try:
            import keyboard
            keyboard.add_hotkey(
                "ctrl+x",
                lambda: threading.Timer(0.1, self.pdf.save_clipboard).start(),
                suppress=False,
            )
            self._last_c = 0.0
            keyboard.on_press_key("c", self._on_c_press)
        except Exception as e:
            logger.error(f"Hotkeys setup: {e}")

    def _on_c_press(self, event) -> None:
        try:
            import keyboard
            import time
            if keyboard.is_pressed("ctrl"):
                now = time.time()
                if now - self._last_c < 0.4:
                    threading.Timer(0.15, self.translator.process_word).start()
                    self._last_c = 0.0
                else:
                    self._last_c = now
        except Exception as e:
            logger.error(f"_on_c_press: {e}")

    # ─ـ Toast ─────────────────────────────────────────────────────────────
    def _show_toast(self, word: str, data: dict) -> None:
        def _build():
            from config import C
            t = tk.Toplevel(self.root)
            t.overrideredirect(True)
            t.attributes("-topmost", True)
            t.configure(bg=C["surface"])
            frm = tk.Frame(t, bg=C["surface"], padx=15, pady=12,
                           highlightbackground=C["border"], highlightthickness=1)
            frm.pack()
            tk.Label(frm, text=f"✅  {word}", bg=C["surface"],
                     fg=C["green"], font=("Consolas", 11, "bold")).pack()
            tk.Label(frm, text=f"→  {data.get('translation','')}", bg=C["surface"],
                     fg=C["text"], font=("Arial", 11, "bold")).pack()
            if ex := data.get("example", ""):
                tk.Label(frm, text=f'"{ex}"', bg=C["surface"],
                         fg=C["text2"], font=("Arial", 9, "italic"),
                         wraplength=360).pack(anchor="w", pady=(3, 0))
            t.update_idletasks()
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            w2, h2 = t.winfo_reqwidth(), t.winfo_reqheight()
            t.geometry(f"+{sw - w2 - 20}+{sh - h2 - 60}")
            t.after(5000, t.destroy)
        self.root.after(0, _build)

    # ─ـ Tray ──────────────────────────────────────────────────────────────
    def _setup_tray(self) -> None:
        try:
            import pystray
            from PIL import Image, ImageDraw

            def _make_icon():
                img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
                d = ImageDraw.Draw(img)
                d.ellipse([2, 2, 62, 62], fill=(74, 144, 217, 255))
                return img

            self.tray = pystray.Icon("SA80", _make_icon(), "مساعد المذاكرة v8.0")
            # FIX: كان threading غير مستورد هنا — أصبح مستورداً في أعلى الملف
            threading.Thread(target=self.tray.run, daemon=True).start()
        except Exception as e:
            logger.error(f"Tray setup: {e}")

    def _update_tray(self) -> None:
        pass

    def run(self) -> None:
        self.dashboard.show()
        self.root.mainloop()


# ── نقطة الدخول ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = StudyAssistant()
    app.run()
