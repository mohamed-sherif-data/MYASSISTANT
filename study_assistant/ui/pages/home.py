# ui/pages/home.py
"""
الصفحة الرئيسية — الجلسة، البومودورو، كلمة اليوم، التقدم اليومي.
تعتمد على StudyAssistant.app.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING
from datetime import date

from config import C, LEVEL_COLORS
from services.tts import HAS_TTS

if TYPE_CHECKING:
    from main import StudyAssistant


class HomePage(tk.Frame):
    """الصفحة الرئيسية للوحة التحكم."""

    def __init__(self, parent: tk.Widget, app: StudyAssistant) -> None:
        super().__init__(parent, bg=C["bg"])
        self.app = app
        self._build()

    def _build(self) -> None:
        # ── بطاقة الجلسة ─────────────────────────────────────────────────
        sess_card = self._card("🎓 الجلسة الدراسية")
        sess_card.pack(fill="x", padx=16, pady=(14, 6))

        self.lbl_session = tk.Label(sess_card, text="لا توجد جلسة", bg=C["card_bg"],
                                     fg=C["text2"], font=("Arial", 12))
        self.lbl_session.pack(pady=(0, 6))

        btn_frame = tk.Frame(sess_card, bg=C["card_bg"])
        btn_frame.pack()
        tk.Button(btn_frame, text="➕ بدء جلسة", command=self._start_session,
                  bg=C["primary"], fg="white", font=("Arial", 10, "bold"),
                  relief="flat", padx=14, pady=6, cursor="hand2").pack(side="left", padx=3)
        tk.Button(btn_frame, text="🔚 إنهاء", command=self._end_session,
                  bg=C["surface2"], fg=C["text2"], font=("Arial", 10),
                  relief="flat", padx=14, pady=6, cursor="hand2").pack(side="left", padx=3)

        # ── بطاقة البومودورو ──────────────────────────────────────────────
        pomo_card = self._card("🍅 البومودورو")
        pomo_card.pack(fill="x", padx=16, pady=6)

        self.lbl_phase = tk.Label(pomo_card, text="متوقف", bg=C["card_bg"],
                                   fg=C["text2"], font=("Arial", 11))
        self.lbl_phase.pack()
        self.lbl_time = tk.Label(pomo_card, text="25:00", bg=C["card_bg"],
                                  fg=C["text"], font=("Consolas", 42, "bold"))
        self.lbl_time.pack(pady=4)

        ctrl = tk.Frame(pomo_card, bg=C["card_bg"])
        ctrl.pack()
        for sym, cmd, clr in [
            ("▶",  self.app.pomodoro.start, C["primary"]),
            ("⏸", self.app.pomodoro.pause, C["warning"]),
            ("⏭", self.app.pomodoro.skip,  C["accent"]),
            ("⏹", self.app.pomodoro.stop,  C["danger"]),
        ]:
            tk.Button(ctrl, text=sym, command=cmd, bg=clr, fg="white",
                      font=("Arial", 14), relief="flat", width=3,
                      cursor="hand2").pack(side="left", padx=3)

        # ── كلمة اليوم ────────────────────────────────────────────────────
        wod_card = self._card("💡 كلمة اليوم")
        wod_card.pack(fill="x", padx=16, pady=6)
        self.wod_frame = tk.Frame(wod_card, bg=C["card_bg"])
        self.wod_frame.pack(fill="x")
        self._build_wod()

        # ─ـ التقدم اليومي ──────────────────────────────────────────────────
        prog_card = self._card("🔥 التقدم اليومي")
        prog_card.pack(fill="x", padx=16, pady=(6, 14))

        row = tk.Frame(prog_card, bg=C["card_bg"])
        row.pack(fill="x")

        self.streak_val = tk.Label(row, text="0", bg=C["card_bg"],
                                    fg=C["warning"], font=("Consolas", 36, "bold"))
        self.streak_val.pack(side="left", expand=True)
        tk.Label(row, text="يوم متواصل", bg=C["card_bg"],
                 fg=C["text2"], font=("Arial", 9)).pack(side="left")

        self.words_today_val = tk.Label(row, text="0", bg=C["card_bg"],
                                         fg=C["green"], font=("Consolas", 36, "bold"))
        self.words_today_val.pack(side="left", expand=True)
        tk.Label(row, text="كلمة اليوم", bg=C["card_bg"],
                 fg=C["text2"], font=("Arial", 9)).pack(side="left")

        self.challenge_val = tk.Label(row, text="", bg=C["card_bg"],
                                       fg=C["warning"], font=("Arial", 9))
        self.challenge_val.pack(side="left", expand=True)

        # بدء التحديث الدوري للصفحة
        self._refresh()

    def _card(self, title: str) -> tk.Frame:
        """بطاقة موحدة الشكل."""
        frame = tk.Frame(self, bg=C["card_bg"], padx=14, pady=10,
                         highlightbackground=C["border"], highlightthickness=1)
        tk.Label(frame, text=title, bg=C["card_bg"], fg=C["text2"],
                 font=("Arial", 9, "bold")).pack(anchor="w", pady=(0, 6))
        return frame

    def _build_wod(self) -> None:
        """عرض كلمة اليوم (تُبنى مرة واحدة ثم تُحدث)."""
        for w in self.wod_frame.winfo_children():
            w.destroy()
        wod = self.app.db.get_word_of_the_day() if hasattr(self.app.db, 'get_word_of_the_day') else None
        if not wod:
            tk.Label(self.wod_frame, text="أضف كلمات أولاً",
                     bg=C["card_bg"], fg=C["text3"], font=("Arial", 9)).pack()
            return
        tk.Label(self.wod_frame, text=wod["word"], bg=C["card_bg"],
                 fg=C["text"], font=("Georgia", 16, "bold")).pack(anchor="w")
        tk.Label(self.wod_frame, text=wod["translation"], bg=C["card_bg"],
                 fg=C["green"], font=("Arial", 11)).pack(anchor="w")
        if ex := wod.get("example", ""):
            tk.Label(self.wod_frame, text=f'"{ex}"', bg=C["card_bg"],
                     fg=C["text2"], font=("Arial", 9, "italic")).pack(anchor="w")

    def _refresh(self) -> None:
        """تحديث البيانات الظاهرة كل ثانية."""
        try:
            # الجلسة
            if self.app.session.active:
                self.lbl_session.config(text=self.app.session.status())
            else:
                self.lbl_session.config(text="لا توجد جلسة نشطة")

            # البومودورو
            p = self.app.pomodoro
            self.lbl_phase.config(text=p.status_label())
            self.lbl_time.config(text=p.time_str())

            # التقدم اليومي
            self.streak_val.config(text=str(self.app.xp.get_streak()))
            today_words = self.app.db.get_daily_stats(date.today().isoformat()).get("words_added", 0)
            self.words_today_val.config(text=str(today_words))

            ch = self.app.challenge.get()
            self.challenge_val.config(text=f"{'✅' if ch.get('completed') else '🎯'} {ch.get('text','')}")

        except Exception:
            pass
        self.after(1000, self._refresh)

    def _start_session(self) -> None:
        """فتح نافذة بدء جلسة (مؤقتة)."""
        from tkinter import simpledialog
        subj = simpledialog.askstring("بدء جلسة", "المادة:")
        lec  = simpledialog.askinteger("بدء جلسة", "رقم المحاضرة:", minvalue=1)
        if subj and lec:
            self.app.session.start(subj, lec)
            self.app.pdf.set_lecture(subj, lec)

    def _end_session(self) -> None:
        self.app.session.end(self.app.pomodoro.work_minutes)
        if self.app.pomodoro.running:
            self.app.pomodoro.stop()