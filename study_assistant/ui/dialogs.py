# ui/dialogs.py
"""
نوافذ صغيرة: بدء جلسة، إعدادات البومودورو.
"""

from __future__ import annotations

import json
import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

from config import C, DEFAULT_SUBJECTS

if TYPE_CHECKING:
    from main import StudyAssistant


class SessionStartDialog:
    """نافذة بدء جلسة دراسة."""

    def __init__(self, app: StudyAssistant) -> None:
        self.app = app

    def show(self) -> None:
        win = tk.Toplevel(self.app.root)
        win.title("بدء جلسة")
        win.configure(bg=C["bg"])
        win.attributes("-topmost", True)
        win.resizable(False, False)
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        win.geometry(f"380x390+{(sw-380)//2}+{(sh-390)//2}")

        f = tk.Frame(win, bg=C["bg"], padx=20, pady=16)
        f.pack(fill="both", expand=True)

        tk.Label(f, text="🎓 جلسة دراسة جديدة", bg=C["bg"], fg=C["text"],
                 font=("Arial", 13, "bold")).pack(pady=(0, 14))

        # المادة
        tk.Label(f, text="المادة:", bg=C["bg"], fg=C["text2"],
                 font=("Arial", 9)).pack(anchor="w")
        subjects = json.loads(self.app.db.get_setting("subjects",
                               json.dumps(DEFAULT_SUBJECTS, ensure_ascii=False)))
        subj_var = tk.StringVar(value=subjects[0])
        ttk.Combobox(f, textvariable=subj_var, values=subjects,
                     state="readonly", font=("Arial", 10)).pack(fill="x", pady=(4, 10))

        # رقم المحاضرة
        tk.Label(f, text="رقم المحاضرة:", bg=C["bg"], fg=C["text2"],
                 font=("Arial", 9)).pack(anchor="w")
        lec_var = tk.IntVar(value=1)
        ttk.Spinbox(f, from_=1, to=50, textvariable=lec_var,
                    font=("Arial", 10), width=8).pack(anchor="w", pady=(4, 10))

        # المدة
        tk.Label(f, text="المدة (ساعات):", bg=C["bg"], fg=C["text2"],
                 font=("Arial", 9)).pack(anchor="w")
        dur_var = tk.DoubleVar(value=3.0)
        ttk.Spinbox(f, from_=0.5, to=12, increment=0.5, textvariable=dur_var,
                    font=("Arial", 10), width=6).pack(anchor="w", pady=(4, 10))

        # بدء البومودورو تلقائياً
        pomo_var = tk.BooleanVar(value=True)
        tk.Checkbutton(f, text="🍅 بدء البومودورو تلقائياً", variable=pomo_var,
                       bg=C["bg"], fg=C["text"], selectcolor=C["surface2"],
                       font=("Arial", 9)).pack(anchor="w", pady=4)

        def _go():
            subj = subj_var.get()
            lec = lec_var.get()
            dur = dur_var.get()
            self.app.session.start(subj, lec, dur)
            self.app.pdf.set_lecture(subj, lec)
            if pomo_var.get() and not self.app.pomodoro.running:
                self.app.pomodoro.start()
            win.destroy()

        tk.Button(f, text="🚀 بدء الجلسة", command=_go,
                  bg=C["primary"], fg="white",
                  font=("Arial", 11, "bold"), relief="flat",
                  padx=20, pady=8).pack(pady=10)


class PomodoroSettingsDialog:
    """نافذة إعدادات البومودورو."""

    def __init__(self, app: StudyAssistant) -> None:
        self.app = app

    def show(self) -> None:
        win = tk.Toplevel(self.app.root)
        win.title("إعدادات البومودورو")
        win.configure(bg=C["bg"])
        win.attributes("-topmost", True)
        win.resizable(False, False)
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        win.geometry(f"360x370+{(sw-360)//2}+{(sh-370)//2}")

        f = tk.Frame(win, bg=C["bg"], padx=20, pady=16)
        f.pack(fill="both", expand=True)
        tk.Label(f, text="⚙ إعدادات البومودورو", bg=C["bg"], fg=C["text"],
                 font=("Arial", 13, "bold")).pack(pady=(0, 14))

        cfg = self.app.pomodoro.cfg
        int_vars = {}
        for label, key, mn, mx in [
            ("مدة العمل (دقيقة)",     "work_duration",      1, 90),
            ("استراحة قصيرة",         "short_break",        1, 30),
            ("استراحة طويلة",         "long_break",         5, 60),
            ("دورات قبل الطويلة",     "cycles_before_long", 2, 8),
        ]:
            row = tk.Frame(f, bg=C["bg"])
            row.pack(fill="x", pady=3)
            tk.Label(row, text=label, bg=C["bg"], fg=C["text2"],
                     font=("Arial", 9), width=26, anchor="w").pack(side="left")
            var = tk.IntVar(value=cfg.get(key, 25))
            int_vars[key] = var
            ttk.Spinbox(row, from_=mn, to=mx, textvariable=var,
                        width=6, font=("Arial", 10)).pack(side="right")

        ttk.Separator(f, orient="horizontal").pack(fill="x", pady=10)

        # مؤثرات صوتية وملخص PDF
        bool_vars = {}
        sound_var = tk.BooleanVar(value=cfg.get("sound_enabled", True))
        bool_vars["sound_enabled"] = sound_var
        tk.Checkbutton(f, text="🔔 إشعارات صوتية", variable=sound_var,
                       bg=C["bg"], fg=C["text"], selectcolor=C["surface2"],
                       font=("Arial", 9)).pack(anchor="w", pady=2)

        summary_var = tk.BooleanVar(value=cfg.get("add_summary", True))
        bool_vars["add_summary"] = summary_var
        tk.Checkbutton(f, text="📄 ملخص PDF", variable=summary_var,
                       bg=C["bg"], fg=C["text"], selectcolor=C["surface2"],
                       font=("Arial", 9)).pack(anchor="w", pady=2)

        def _save():
            for k, v in int_vars.items():
                self.app.pomodoro.cfg[k] = v.get()
            for k, v in bool_vars.items():
                self.app.pomodoro.cfg[k] = v.get()
            self.app.pomodoro.save_config()
            win.destroy()

        tk.Button(f, text="💾 حفظ", command=_save,
                  bg=C["accent"], fg="white",
                  font=("Arial", 11, "bold"), relief="flat",
                  padx=20, pady=8).pack(pady=14)