# ui/pages/settings.py
"""
صفحة الإعدادات — Groq API، البومودورو، المواد.
"""

from __future__ import annotations

import json
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from typing import TYPE_CHECKING

from config import C, DEFAULT_SUBJECTS
from services.groq_client import GROQ_MODELS

if TYPE_CHECKING:
    from main import StudyAssistant


class SettingsPage(tk.Frame):
    def __init__(self, parent: tk.Widget, app: StudyAssistant) -> None:
        super().__init__(parent, bg=C["bg"])
        self.app = app
        self._build()

    def _build(self) -> None:
        canvas = tk.Canvas(self, bg=C["bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=C["bg"])
        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # العمل داخل scroll_frame
        f = scroll_frame
        tk.Label(f, text="⚙️ الإعدادات", bg=C["bg"], fg=C["text"],
                 font=("Arial", 15, "bold")).pack(anchor="w", padx=20, pady=16)

        # ── Groq API ───────────────────────────────────────────────────────
        gc = self._card(f, "⚡ Groq API Key")
        gc.pack(fill="x", padx=20, pady=(0, 10))

        status_clr = C["green"] if self.app.groq.is_ready else C["danger"]
        status_txt = "✅ متصل" if self.app.groq.is_ready else "❌ غير متصل"
        tk.Label(gc, text=status_txt, bg=C["card_bg"], fg=status_clr,
                 font=("Arial", 10)).pack(anchor="w")

        tk.Label(gc, text="النموذج:", bg=C["card_bg"], fg=C["text2"],
                 font=("Arial", 9)).pack(anchor="w", pady=(8, 2))
        self.model_var = tk.StringVar(value=self.app.groq.model)
        ttk.Combobox(gc, textvariable=self.model_var, values=GROQ_MODELS,
                     state="readonly", font=("Consolas", 9)).pack(fill="x", pady=(0, 6))

        tk.Label(gc, text="API Key:", bg=C["card_bg"], fg=C["text2"],
                 font=("Arial", 9)).pack(anchor="w", pady=(4, 2))
        key_row = tk.Frame(gc, bg=C["card_bg"])
        key_row.pack(fill="x")
        self.key_var = tk.StringVar(value=self.app.db.get_setting("GROQ_API_KEY", ""))
        tk.Entry(key_row, textvariable=self.key_var, bg=C["surface2"], fg=C["text"],
                 font=("Consolas", 9), relief="flat", bd=6, show="*").pack(side="left", fill="x", expand=True)
        tk.Button(key_row, text="💾 حفظ واختبار",
                  command=self._save_groq,
                  bg=C["accent"], fg="white", font=("Arial", 9),
                  relief="flat", padx=10, pady=4).pack(side="left", padx=(8, 0))

        # ─ـ المواد ─────────────────────────────────────────────────────────
        sc = self._card(f, "📚 إدارة المواد")
        sc.pack(fill="x", padx=20, pady=(0, 10))
        self.subj_frame = tk.Frame(sc, bg=C["card_bg"])
        self.subj_frame.pack(fill="x", pady=(0, 8))
        add_row = tk.Frame(sc, bg=C["card_bg"])
        add_row.pack(fill="x")
        self.new_subj_var = tk.StringVar()
        tk.Entry(add_row, textvariable=self.new_subj_var, bg=C["surface2"],
                 fg=C["text"], font=("Arial", 10), relief="flat", bd=6).pack(side="left", fill="x", expand=True)
        tk.Button(add_row, text="➕ إضافة", command=self._add_subject,
                  bg=C["primary"], fg="white", font=("Arial", 9),
                  relief="flat", padx=10, pady=5).pack(side="left", padx=(6, 0))
        self._refresh_subjects()

        # ─ـ البومودورو ─────────────────────────────────────────────────────
        bc = self._card(f, "🍅 إعدادات البومودورو")
        bc.pack(fill="x", padx=20, pady=(0, 10))
        tk.Button(bc, text="⚙ فتح إعدادات البومودورو",
                  command=self._pomo_settings,
                  bg=C["surface2"], fg=C["text2"], font=("Arial", 10),
                  relief="flat", padx=14, pady=6).pack(anchor="w")

    def _card(self, parent, title: str) -> tk.Frame:
        frame = tk.Frame(parent, bg=C["card_bg"], padx=14, pady=10,
                         highlightbackground=C["border"], highlightthickness=1)
        tk.Label(frame, text=title, bg=C["card_bg"], fg=C["text2"],
                 font=("Arial", 9, "bold")).pack(anchor="w", pady=(0, 6))
        return frame

    def _save_groq(self) -> None:
        key = self.key_var.get().strip()
        model = self.model_var.get()
        if not key or len(key) < 20:
            messagebox.showwarning("تنبيه", "المفتاح قصير جداً")
            return
        def _test():
            success = self.app.groq.set_key(key, model)
            if success:
                messagebox.showinfo("Groq ✅", "تم الاتصال بنجاح!")
            else:
                messagebox.showerror("Groq ❌", "فشل الاتصال")
        threading.Thread(target=_test, daemon=True).start()

    def _refresh_subjects(self) -> None:
        for w in self.subj_frame.winfo_children():
            w.destroy()
        subjects = json.loads(self.app.db.get_setting("subjects",
                               json.dumps(DEFAULT_SUBJECTS, ensure_ascii=False)))
        for s in subjects:
            row = tk.Frame(self.subj_frame, bg=C["card_bg"])
            row.pack(fill="x", pady=1)
            tk.Label(row, text=s, bg=C["card_bg"], fg=C["text"],
                     font=("Arial", 10)).pack(side="left", padx=4)
            if s != "بدون مادة":
                tk.Button(row, text="✕", command=lambda sub=s: self._del_subject(sub),
                          bg=C["card_bg"], fg=C["danger"], font=("Arial", 9),
                          relief="flat", padx=4, cursor="hand2").pack(side="right")

    def _add_subject(self) -> None:
        name = self.new_subj_var.get().strip()
        if not name:
            return
        subjects = json.loads(self.app.db.get_setting("subjects",
                               json.dumps(DEFAULT_SUBJECTS, ensure_ascii=False)))
        if name not in subjects:
            subjects.append(name)
            self.app.db.set_setting("subjects", json.dumps(subjects, ensure_ascii=False))
        self.new_subj_var.set("")
        self._refresh_subjects()

    def _del_subject(self, name: str) -> None:
        subjects = json.loads(self.app.db.get_setting("subjects",
                               json.dumps(DEFAULT_SUBJECTS, ensure_ascii=False)))
        if name in subjects and name != "بدون مادة":
            subjects.remove(name)
            self.app.db.set_setting("subjects", json.dumps(subjects, ensure_ascii=False))
            self._refresh_subjects()

    def _pomo_settings(self) -> None:
        # فتح إعدادات البومودورو
        from ui.dialogs import PomodoroSettingsDialog
        PomodoroSettingsDialog(self.app).show()