# ui/pages/settings.py
"""
صفحة الإعدادات — جديدة كلياً مع واجهة نظيفة ومنظمة
"""

from __future__ import annotations

import json
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from typing import TYPE_CHECKING
import webbrowser

from config import C, DEFAULT_SUBJECTS, PREPOSITIONS, DEFAULT_HOTKEY
from services.groq_client import GROQ_MODELS

if TYPE_CHECKING:
    from main import StudyAssistant


class SettingsPage(tk.Frame):
    def __init__(self, parent: tk.Widget, app: StudyAssistant) -> None:
        super().__init__(parent, bg=C["bg"])
        self.app = app
        self._build()

    def _build(self) -> None:
        """تصميم جديد - شبكة من البطاقات"""
        # عنوان الصفحة
        header = tk.Frame(self, bg=C["bg"])
        header.pack(fill="x", padx=20, pady=20)
        
        tk.Label(header, text="⚙️ الإعدادات", bg=C["bg"], fg=C["text"],
                font=("Arial", 18, "bold")).pack(side="left")
        
        # إطار رئيسي للبطاقات
        main_frame = tk.Frame(self, bg=C["bg"])
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # صف - البطاقات الثلاثة الرئيسية
        top_row = tk.Frame(main_frame, bg=C["bg"])
        top_row.pack(fill="x", pady=5)
        
        # 🔧 إعدادات API
        self._build_api_card(top_row)
        
        # 📚 المواد
        self._build_subjects_card(top_row)
        
        # 🍅 البومودورو
        self._build_pomo_card(top_row)
        
        # صف ثاني -الميزات الجديدة
        mid_row = tk.Frame(main_frame, bg=C["bg"])
        mid_row.pack(fill="x", pady=5)
        
        # 💬 Chatbot
        self._build_chatbot_card(mid_row)
        
        # 🔑 مفاتيح API الإضافية
        self._build_keys_card(mid_row)
        
        # صف ثالث - الأدوات
        bottom_row = tk.Frame(main_frame, bg=C["bg"])
        bottom_row.pack(fill="x", pady=5)
        
        # ⌨️ اختصار التفعيل
        self._build_hotkey_card(bottom_row)
        
        # 📖 حروف الجر
        self._build_prepositions_card(bottom_row)
        
        # 🎵 الأصوات
        self._build_sounds_card(bottom_row)

    def _build_card(self, parent, title: str, emoji: str) -> tk.Frame:
        """إنشاء بطاقة موحدة"""
        card = tk.Frame(parent, bg=C["surface"], bd=1, relief="solid")
        card.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        
        # عنوان البطاقة
        tk.Label(card, text=f"{emoji} {title}", bg=C["surface"], fg=C["text"],
                font=("Arial", 11, "bold"), pady=8).pack(anchor="w", padx=12)
        
        # خط فاصل
        tk.Frame(card, bg=C["border"], height=1).pack(fill="x", padx=12)
        
        # محتوى البطاقة
        content = tk.Frame(card, bg=C["surface"])
        content.pack(fill="both", expand=True, padx=12, pady=8)
        
        return content

    def _build_api_card(self, parent):
        """البطاقة الأولى - إعدادات API"""
        c = self._build_card(parent, "API الرئيسي", "🔑")
        
        # حالة الاتصال
        status_clr = C.get("green", "#2ea043") if self.app.groq.is_ready else C.get("danger", "#da3633")
        status_txt = "✅ متصل" if self.app.groq.is_ready else "❌ غير متصل"
        tk.Label(c, text=status_txt, bg=C["surface"], fg=status_clr, font=("Arial", 9)).pack(anchor="w")
        
        # نموذج AI
        tk.Label(c, text="النموذج:", bg=C["surface"], fg=C.get("text2", "#8b949e"), font=("Arial", 8)).pack(anchor="w", pady=(8, 2))
        self.model_var = tk.StringVar(value=self.app.groq.model)
        model_combo = ttk.Combobox(c, textvariable=self.model_var, values=GROQ_MODELS, state="readonly", font=("Consolas", 8))
        model_combo.pack(fill="x", pady=(0, 8))
        model_combo.bind("<<ComboboxSelected>>", lambda e: self._save_groq())
        
        # API Key
        tk.Label(c, text="API Key:", bg=C["surface"], fg=C.get("text2", "#8b949e"), font=("Arial", 8)).pack(anchor="w", pady=(4, 2))
        key_row = tk.Frame(c, bg=C["surface"])
        key_row.pack(fill="x")
        self.key_var = tk.StringVar(value=self.app.db.get_setting("GROQ_API_KEY", ""))
        tk.Entry(key_row, textvariable=self.key_var, bg=C.get("surface2", "#21262d"), fg=C["text"],
                font=("Consolas", 8), relief="flat", bd=4, show="•").pack(side="left", fill="x", expand=True)
        tk.Button(key_row, text="💾", command=self._save_groq, bg=C.get("accent", "#1f6feb"), fg="white",
                font=("Arial", 9), relief="flat", padx=8).pack(side="left", padx=(4, 0))

    def _build_subjects_card(self, parent):
        """البطاقة الثانية - المواد"""
        c = self._build_card(parent, "المواد", "📚")
        
        # قائمة المواد
        self.subj_list = tk.Listbox(c, bg=C.get("surface2", "#21262d"), fg=C["text"],
                font=("Arial", 9), height=5, relief="flat", bd=0)
        self.subj_list.pack(fill="both", expand=True, pady=4)
        
        # أزرار المواد
        btn_row = tk.Frame(c, bg=C["surface"])
        btn_row.pack(fill="x")
        
        self.new_subj_var = tk.StringVar()
        tk.Entry(btn_row, textvariable=self.new_subj_var, bg=C.get("surface2", "#21262d"),
                fg=C["text"], font=("Arial", 9), relief="flat", bd=4).pack(side="left", fill="x", expand=True)
        tk.Button(btn_row, text="➕", command=self._add_subject, bg=C.get("primary", "#238636"),
                fg="white", font=("Arial", 9), relief="flat", padx=8).pack(side="left", padx=2)
        tk.Button(btn_row, text="🗑", command=self._del_subject, bg=C.get("danger", "#da3633"),
                fg="white", font=("Arial", 9), relief="flat", padx=8).pack(side="left", padx=2)
        
        self._refresh_subjects()

    def _build_pomo_card(self, parent):
        """البطاقة الثالثة - البومودورو"""
        c = self._build_card(parent, "البومودورو", "🍅")
        
        tk.Button(c, text="⚙️ إعدادات البومودورو", command=self._pomo_settings,
                bg=C.get("surface2", "#21262d"), fg=C["text"], font=("Arial", 10),
                relief="flat", padx=12, pady=8).pack(fill="x")
        
        # عرض الإعدادات الحالية
        cfg = self.app.pomodoro.cfg
        info = f"⏱ عمل: {cfg.get('work_duration', 25)}د | 🧩 راحة: {cfg.get('short_break', 5)}د"
        tk.Label(c, text=info, bg=C["surface"], fg=C.get("text2", "#8b949e"),
                font=("Arial", 8)).pack(pady=4)

    def _build_chatbot_card(self, parent):
        """البطاقة الرابعة - Chatbot"""
        c = self._build_card(parent, "Chatbot المحادثة", "💬")
        
        tk.Label(c, text="تدرب على استخدام الكلمات!", bg=C["surface"],
                fg=C.get("text2", "#8b949e"), font=("Arial", 8)).pack(anchor="w")
        
        tk.Button(c, text="🚀 بدء محادثة", command=self._open_chatbot,
                bg=C.get("primary", "#238636"), fg="white", font=("Arial", 10),
                relief="flat", padx=14, pady=8).pack(fill="x", pady=4)
        
        # اختيار المادة
        tk.Label(c, text="مادة:", bg=C["surface"], fg=C.get("text2", "#8b949e"), font=("Arial", 8)).pack(anchor="w", pady=(4, 2))
        self.chat_subj_var = tk.StringVar()
        subj_combo = ttk.Combobox(c, textvariable=self.chat_subj_var, values=["كل المواد"] + DEFAULT_SUBJECTS,
                                state="readonly", font=("Arial", 9))
        subj_combo.pack(fill="x")

    def _build_keys_card(self, parent):
        """البطاقة الخامسة - مفاتيح API الإضافية"""
        c = self._build_card(parent, "مفاتيح الإضافية", "🔐")
        
        tk.Label(c, text="أضف مفاتيح للدوران التلقائي:", bg=C["surface"],
                fg=C.get("text2", "#8b949e"), font=("Arial", 8)).pack(anchor="w")
        
        add_row = tk.Frame(c, bg=C["surface"])
        add_row.pack(fill="x", pady=4)
        self.extra_key_var = tk.StringVar()
        tk.Entry(add_row, textvariable=self.extra_key_var, bg=C.get("surface2", "#21262d"),
                fg=C["text"], font=("Consolas", 8), relief="flat", bd=4, show="•").pack(side="left", fill="x", expand=True)
        tk.Button(add_row, text="➕", command=self._add_extra_key, bg=C.get("primary", "#238636"),
                fg="white", font=("Arial", 9), relief="flat", padx=8).pack(side="left", padx=2)
        
        # عرض المفاتيح
        keys = json.loads(self.app.db.get_setting("EXTRA_API_KEYS", "[]"))
        if keys:
            tk.Label(c, text=f"📋 {len(keys)} مفتاح محفوظ", bg=C["surface"],
                    fg=C.get("green", "#2ea043"), font=("Arial", 8)).pack(anchor="w", pady=4)

    def _build_hotkey_card(self, parent):
        """البطاقة السادسة - اختصار التفعيل"""
        c = self._build_card(parent, "اختصار التفعيل", "⌨️")
        
        tk.Label(c, text="اختصار فتح النافذة:", bg=C["surface"],
                fg=C.get("text2", "#8b949e"), font=("Arial", 8)).pack(anchor="w")
        
        hk_row = tk.Frame(c, bg=C["surface"])
        hk_row.pack(fill="x", pady=4)
        self.hotkey_var = tk.StringVar(value=self.app.db.get_setting("hotkey", DEFAULT_HOTKEY))
        tk.Entry(hk_row, textvariable=self.hotkey_var, bg=C.get("surface2", "#21262d"),
                fg=C["text"], font=("Consolas", 11), relief="flat", bd=4).pack(side="left", fill="x", expand=True)
        tk.Button(hk_row, text="💾", command=self._save_hotkey, bg=C.get("accent", "#1f6feb"),
                fg="white", font=("Arial", 9), relief="flat", padx=8).pack(side="left", padx=(4, 0))
        
        tk.Label(c, text="مثال: Ctrl+Shift+S", bg=C["surface"],
                fg=C.get("text3", "#6e7681"), font=("Arial", 7)).pack(anchor="w", pady=(2, 0))

    def _build_prepositions_card(self, parent):
        """البطاقة السابعة - حروف الجر"""
        c = self._build_card(parent, "حروف الجر", "📖")
        
        # عرض كمergi数量的
        prep_text = ", ".join(PREPOSITIONS[:10]) + "..."
        tk.Label(c, text=prep_text, bg=C["surface"], fg=C.get("text2", "#8b949e"),
                font=("Consolas", 8), wraplength=200, justify="left").pack(anchor="w")
        
        tk.Button(c, text="📋 نسخ الكل", command=self._copy_preps,
                bg=C.get("surface2", "#21262d"), fg=C["text"], font=("Arial", 8),
                relief="flat", padx=8, pady=4).pack(anchor="w", pady=4)

    def _build_sounds_card(self, parent):
        """البطاقة الثامنة - الأصوات"""
        c = self._build_card(parent, "الأصوات", "🔊")
        
        # صوت الإشعارات
        self.sound_var = tk.BooleanVar(value=self.app.pomodoro.cfg.get("sound_enabled", True))
        tk.Checkbutton(c, text="صوت الإشعارات", variable=self.sound_var, bg=C["surface"],
                fg=C["text"], command=self._save_sound_settings).pack(anchor="w")
        
        # صوت مخصص
        tk.Label(c, text="صوت مخصص:", bg=C["surface"],
                fg=C.get("text2", "#8b949e"), font=("Arial", 8)).pack(anchor="w", pady=(8, 2))
        
        sound_row = tk.Frame(c, bg=C["surface"])
        sound_row.pack(fill="x")
        self.custom_sound_var = tk.StringVar(value=self.app.pomodoro.cfg.get("custom_sound", ""))
        tk.Entry(sound_row, textvariable=self.custom_sound_var, bg=C.get("surface2", "#21262d"),
                fg=C["text"], font=("Consolas", 8), relief="flat", bd=4).pack(side="left", fill="x", expand=True)
        tk.Button(sound_row, text="📁", command=self._browse_sound, bg=C.get("surface2", "#21262d"),
                fg=C["text"], font=("Arial", 9), relief="flat", padx=6).pack(side="left", padx=2)

    # ──── دوال ─────────────────────────────────────────────────────────────

    def _save_groq(self) -> None:
        key = self.key_var.get().strip()
        model = self.model_var.get().strip()
        
        if key:
            self.app.db.set_setting("GROQ_API_KEY", key)
        if model:
            self.app.db.set_setting("groq_model", model)
        
        # إعادة تحميل
        self.app.groq.api_key = key or self.app.db.get_setting("GROQ_API_KEY", "")
        self.app.groq.model = model or self.app.db.get_setting("groq_model", "mixtral-8x7b-32768")
        
        messagebox.showinfo("✅", "تم حفظ إعدادات API!")

    def _refresh_subjects(self) -> None:
        self.subj_list.delete(0, "end")
        subjects = self.app.db.get_subjects()
        for s in sorted(subjects):
            self.subj_list.insert("end", s)

    def _add_subject(self) -> None:
        new_subj = self.new_subj_var.get().strip()
        if new_subj and new_subj not in self.app.db.get_subjects():
            self.app.db.add_subject(new_subj)
            self.new_subj_var.set("")
            self._refresh_subjects()
            messagebox.showinfo("✅", f"تمت إضافة: {new_subj}")

    def _del_subject(self) -> None:
        sel = self.subj_list.curselection()
        if sel:
            subj = self.subj_list.get(sel[0])
            if subj and subj != "بدون مادة":
                self.app.db.delete_subject(subj)
                self._refresh_subjects()
                messagebox.showinfo("✅", f"تم حذف: {subj}")

    def _pomo_settings(self) -> None:
        from ui.dialogs import PomodoroSettingsDialog
        PomodoroSettingsDialog(self.app)

    def _open_chatbot(self) -> None:
        from ui.chatbot import ChatbotWindow
        subj = self.chat_subj_var.get()
        if subj and subj != "كل المواد":
            self.app.chatbot.set_subject(subj)
        ChatbotWindow(self.app).show()

    def _add_extra_key(self) -> None:
        key = self.extra_key_var.get().strip()
        if key:
            keys = json.loads(self.app.db.get_setting("EXTRA_API_KEYS", "[]"))
            if key not in keys:
                keys.append(key)
                self.app.db.set_setting("EXTRA_API_KEYS", json.dumps(keys))
                self.extra_key_var.set("")
                messagebox.showinfo("✅", "تم إضافة المفتاح!")

    def _save_hotkey(self) -> None:
        hotkey = self.hotkey_var.get().strip()
        if hotkey:
            self.app.db.set_setting("hotkey", hotkey)
            messagebox.showinfo("✅", f"تم!\nالاختصار: {hotkey}\nأعد تشغيل التطبيق")

    def _copy_preps(self) -> None:
        self.clipboard_clear()
        self.clipboard_append(", ".join(PREPOSITIONS))
        messagebox.showinfo("✅", "تم نسخ حروف الجر!")

    def _save_sound_settings(self) -> None:
        self.app.pomodoro.cfg["sound_enabled"] = self.sound_var.get()
        self.app.pomodoro.save_config()

    def _browse_sound(self) -> None:
        from tkinter import filedialog
        file = filedialog.askopenfilename(filetypes=[("Audio", "*.wav *.mp3 *.ogg")])
        if file:
            self.custom_sound_var.set(file)
            self.app.pomodoro.cfg["custom_sound"] = file
            self.app.pomodoro.save_config()
            messagebox.showinfo("✅", "تم تحديد الصوت!")