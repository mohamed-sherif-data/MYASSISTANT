# ui/pages/review.py
"""
صفحة المراجعة — الكلمات المستحقة، إحصائيات، أزرار البطاقات والاختبار.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from typing import TYPE_CHECKING

from config import C, LEVEL_COLORS
from services.tts import HAS_TTS

if TYPE_CHECKING:
    from main import StudyAssistant


class ReviewPage(tk.Frame):
    def __init__(self, parent: tk.Widget, app: StudyAssistant) -> None:
        super().__init__(parent, bg=C["bg"])
        self.app = app
        self._build()

    def _build(self) -> None:
        # العنوان
        tk.Label(self, text="🃏 مراجعة الكلمات", bg=C["bg"], fg=C["text"],
                 font=("Arial", 15, "bold")).pack(anchor="w", padx=20, pady=16)

        # فلتر المادة
        filter_frame = tk.Frame(self, bg=C["bg"])
        filter_frame.pack(fill="x", padx=20, pady=(0, 8))
        tk.Label(filter_frame, text="المادة:", bg=C["bg"], fg=C["text2"],
                 font=("Arial", 9)).pack(side="left", padx=(0,6))
        self.subject_var = tk.StringVar(value="الكل")
        self.subject_combo = ttk.Combobox(filter_frame, textvariable=self.subject_var,
                                          values=["الكل"], state="readonly",
                                          font=("Arial", 10), width=18)
        self.subject_combo.pack(side="left")
        self.subject_combo.bind("<<ComboboxSelected>>", lambda e: self._refresh())

        # إحصائيات سريعة (3 بطاقات)
        stats_frame = tk.Frame(self, bg=C["bg"])
        stats_frame.pack(fill="x", padx=20, pady=(0, 10))
        self.stat_labels = []
        for title in ["📚 إجمالي", "🔔 مستحق اليوم", "✅ دقة المراجعة"]:
            card = self._mini_card(stats_frame, title)
            card.pack(side="left", expand=True, fill="x", padx=3)
            val = tk.Label(card, text="—", bg=C["card_bg"], fg=C["text"],
                           font=("Consolas", 20, "bold"))
            val.pack(pady=4)
            self.stat_labels.append(val)

        # أزرار المراجعة
        btn_frame = tk.Frame(self, bg=C["bg"])
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="🃏  بطاقات مراجعة",
                  command=self._open_flashcards,
                  bg=C["primary"], fg="white", font=("Arial", 12, "bold"),
                  relief="flat", padx=22, pady=11, cursor="hand2").pack(side="left", padx=6)
        tk.Button(btn_frame, text="🎯  اختبار Quiz",
                  command=self._open_quiz,
                  bg=C["accent"], fg="white", font=("Arial", 12, "bold"),
                  relief="flat", padx=22, pady=11, cursor="hand2").pack(side="left", padx=6)

        # قائمة الكلمات المستحقة
        tk.Label(self, text="الكلمات المستحقة اليوم", bg=C["bg"], fg=C["text2"],
                 font=("Arial", 10)).pack(anchor="w", padx=20, pady=(10, 4))
        list_frame = tk.Frame(self, bg=C["surface"],
                              highlightbackground=C["border"], highlightthickness=1)
        list_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        self.tree = ttk.Treeview(list_frame, columns=("word","trans","level","ipa"), show="headings", height=8)
        self.tree.heading("word", text="الكلمة")
        self.tree.heading("trans", text="الترجمة")
        self.tree.heading("level", text="المستوى")
        self.tree.heading("ipa", text="IPA")
        self.tree.column("word", width=120, anchor="center")
        self.tree.column("trans", width=140, anchor="center")
        self.tree.column("level", width=60, anchor="center")
        self.tree.column("ipa", width=120, anchor="center")
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.tree.bind("<Double-1>", self._speak_word)

        self._refresh()

    def _mini_card(self, parent: tk.Widget, title: str) -> tk.Frame:
        """بطاقة صغيرة للإحصائيات."""
        frame = tk.Frame(parent, bg=C["card_bg"], padx=10, pady=8,
                         highlightbackground=C["border"], highlightthickness=1)
        tk.Label(frame, text=title, bg=C["card_bg"], fg=C["text3"],
                 font=("Arial", 8)).pack()
        return frame

    def _get_filtered_words(self) -> list[dict]:
        """إرجاع الكلمات بعد تطبيق فلتر المادة."""
        all_words = self.app.db.load_words()
        subj = self.subject_var.get()
        if subj != "الكل":
            return [w for w in all_words if w.get("subject", "") == subj]
        return all_words

    def _get_due_words(self) -> list[dict]:
        """الكلمات المستحقة مع الفلتر."""
        subj = self.subject_var.get()
        due = self.app.db.get_due_words()
        if subj != "الكل":
            due = [w for w in due if w.get("subject", "") == subj]
        return due

    def _refresh(self) -> None:
        """تحديث البيانات في الصفحة."""
        # تحديث قائمة المواد
        subjects = sorted({w.get("subject", "") for w in self.app.db.load_words() if w.get("subject")})
        self.subject_combo.config(values=["الكل"] + subjects)

        words = self._get_filtered_words()
        due = self._get_due_words()

        # إحصائيات
        total = len(words)
        due_count = len(due)
        tr = sum(int(w.get("total_reviews", 0) or 0) for w in words)
        cr = sum(int(w.get("correct_reviews", 0) or 0) for w in words)
        acc = f"{int(cr/tr*100)}%" if tr > 0 else "—"

        self.stat_labels[0].config(text=str(total))
        self.stat_labels[1].config(text=str(due_count))
        self.stat_labels[2].config(text=acc)

        # تحديث الجدول
        for row in self.tree.get_children():
            self.tree.delete(row)
        for w in due[:20]:  # عرض أول 20 كلمة
            self.tree.insert("", "end", values=(
                w.get("word", ""),
                w.get("translation", ""),
                w.get("level", ""),
                w.get("ipa", ""),
            ))

    def _speak_word(self, event=None) -> None:
        """نطق الكلمة المحددة."""
        if not HAS_TTS:
            return
        sel = self.tree.selection()
        if sel:
            word = self.tree.item(sel[0], "values")[0]
            self.app.tts.speak_word(word)

    def _open_flashcards(self) -> None:
        subj = self.subject_var.get()
        # استيراد نافذة البطاقات (سنبنيها قريباً)
        from ui.flashcards import FlashcardsWindow
        FlashcardsWindow(self.app, subject_filter=subj).show()

    def _open_quiz(self) -> None:
        subj = self.subject_var.get()
        from ui.quiz import QuizWindow
        QuizWindow(self.app, default_subject=subj).show()