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
from services.sentence_builder import SentenceBuilder
from services.chatbot import ChatbotPractice
from services.paragraph_processor import ParagraphProcessor

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

        # ─ـ Sentence Builder ────────────────────────────────────────────
        self.sentences = SentenceBuilder(self.groq)

        # ─ـ Chatbot ───────────────────────────────────────────────────────
        self.chatbot = ChatbotPractice(self.groq, self.db)

        # ─ـ Paragraph Processor ────────────────────────────────────────
        self.paragraph = ParagraphProcessor(self.groq, self.db)

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

    # ── Tray + Reminders ───────────────────────────────────────────────────
    def _setup_tray(self) -> None:
        """إعداد أيقونة النظام + قائمة."""
        try:
            import pystray
            from pystray import MenuItem as item, Menu
            from PIL import Image, ImageDraw, ImageFont

            def _make_icon(color: str = "#4a90d9", sub: str = "") -> Image.Image:
                """إنشاء أيقونة ديناميكية."""
                size = 64
                img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
                d = ImageDraw.Draw(img)
                # parse color
                if color.startswith("#"):
                    r = int(color[1:3], 16)
                    g = int(color[3:5], 16)
                    b = int(color[5:7], 16)
                else:
                    r, g, b = 74, 144, 217
                d.ellipse([2, 2, size-2, size-2], fill=(r, g, b, 255))
                return img

            def _build_menu():
                return Menu(
                    item(f"🍅 {self.pomodoro.status_label()}", None, enabled=False),
                    item(f"⏳ {self.pomodoro.time_str()}", None, enabled=False),
                    Menu.SEPARATOR,
                    item("🖥️ لوحة التحكم", lambda i, m: self.root.after(0, self.dashboard.show)),
                    Menu.SEPARATOR,
                    item("▶️ بدء", lambda i, m: self.pomodoro.start(), enabled=not self.pomodoro.running),
                    item("⏸️ مؤقت", lambda i, m: self.pomodoro.pause(), enabled=self.pomodoro.running),
                    item("⏹️ إيقاف", lambda i, m: self.pomodoro.stop(), enabled=self.pomodoro.running),
                    Menu.SEPARATOR,
                    item("🃏 مراجعة", lambda i, m: self.root.after(0, lambda: self._open_review("flashcard"))),
                    item("🎯 اختبار", lambda i, m: self.root.after(0, lambda: self._open_review("quiz"))),
                    item("⏱️ ساعة عائمة", lambda i, m: self.float_timer.toggle()),
                    Menu.SEPARATOR,
                    item("🚪 خروج", self._quit),
                )

            self.tray = pystray.Icon("SA80", _make_icon(), "مساعد المذاكرة v8.0", _build_menu())
            
            # تحديث الأيقونة كل ثانية
            def _update_tray_icon():
                if not hasattr(self, 'tray') or not self.tray:
                    return
                color_map = {
                    "work": "#238636",  # أخضر
                    "short_break": "#d29922",  # أصفر
                    "long_break": "#d29922",
                    "idle": "#4a90d9",  # أزرق
                }
                clr = color_map.get(self.pomodoro.phase, "#4a90d9")
                sub = self.pomodoro.time_str() if self.pomodoro.running else ""
                try:
                    self.tray.icon = _make_icon(clr, sub)
                    self.tray.menu = _build_menu()
                except:
                    pass
                self.root.after(1000, _update_tray_icon)
            
            self.root.after(1500, _update_tray_icon)
            threading.Thread(target=self.tray.run, daemon=True).start()
            logger.info("System tray initialized ✅")
        except Exception as e:
            logger.error(f"Tray setup: {e}")

    def _update_tray(self) -> None:
        """تحديث الأيقونة (يُستدعى من البومودورو)."""
        if hasattr(self, 'tray') and self.tray:
            try:
                import pystray
                from PIL import Image, ImageDraw
                color_map = {"work": "#238636", "short_break": "#d29922", "long_break": "#d29922", "idle": "#4a90d9"}
                clr = color_map.get(self.pomodoro.phase, "#4a90d9")
                size = 64
                img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
                d = ImageDraw.Draw(img)
                r = int(clr[1:3], 16)
                g = int(clr[3:5], 16)
                b = int(clr[5:7], 16)
                d.ellipse([2, 2, size-2, size-2], fill=(r, g, b, 255))
                self.tray.icon = img
            except:
                pass

    def _startup_reminder(self) -> None:
        """تذكير عند التشغيل لو لم تذاكر اليوم."""
        def _check():
            import time as t
            t.sleep(2)
            reminder = self.db.get_setting("study_reminder", "")
            if reminder:
                self.root.after(0, lambda: self._show_reminder(reminder))
        threading.Thread(target=_check, daemon=True).start()

    def _show_reminder(self, msg: str) -> None:
        """عرض نافذة التذكير."""
        from tkinter import messagebox
        messagebox.showinfo("⏰ تذكير", msg)

    def run(self) -> None:
        self.dashboard.show()
        self.root.mainloop()


# ── نقطة الدخول ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = StudyAssistant()
    app.run()
