# ui/pages/stats.py
"""
صفحة الإحصائيات العامة.
"""

from __future__ import annotations

import tkinter as tk
from datetime import date, timedelta
from typing import TYPE_CHECKING

from config import C

if TYPE_CHECKING:
    from main import StudyAssistant


class StatsPage(tk.Frame):
    def __init__(self, parent: tk.Widget, app: StudyAssistant) -> None:
        super().__init__(parent, bg=C["bg"])
        self.app = app
        self._build()

    def _build(self) -> None:
        tk.Label(self, text="📊 إحصائيات الدراسة", bg=C["bg"], fg=C["text"],
                 font=("Arial", 15, "bold")).pack(anchor="w", padx=20, pady=16)

        # بطاقات الإحصائيات
        cards_frame = tk.Frame(self, bg=C["bg"])
        cards_frame.pack(fill="x", padx=20)

        self.card_vals = []
        for title in ["إجمالي الكلمات", "كلمات اليوم", "ساعات الأسبوع", "دقة المراجعة"]:
            card = tk.Frame(cards_frame, bg=C["card_bg"], padx=12, pady=10,
                            highlightbackground=C["border"], highlightthickness=1)
            card.pack(side="left", expand=True, fill="both", padx=3)
            tk.Label(card, text=title, bg=C["card_bg"], fg=C["text3"],
                     font=("Arial", 8)).pack()
            val = tk.Label(card, text="—", bg=C["card_bg"], fg=C["text"],
                           font=("Consolas", 20, "bold"))
            val.pack(pady=4)
            self.card_vals.append(val)

        # خريطة حرارة أسبوعية
        tk.Label(self, text="نشاط آخر 7 أيام", bg=C["bg"], fg=C["text2"],
                 font=("Arial", 10)).pack(anchor="w", padx=20, pady=(18, 4))
        self.heatmap = tk.Frame(self, bg=C["bg"])
        self.heatmap.pack(fill="x", padx=20)

        self._refresh()

    def _refresh(self) -> None:
        db = self.app.db
        words = db.load_words()
        today = date.today().isoformat()

        # إجمالي الكلمات
        total_words = len(words)

        # كلمات اليوم
        today_words = db.get_daily_stats(today).get("words_added", 0)

        # ساعات الأسبوع
        weekly_minutes = 0
        for i in range(7):
            day = (date.today() - timedelta(days=i)).isoformat()
            weekly_minutes += db.get_daily_stats(day).get("minutes", 0)
        weekly_hours = f"{weekly_minutes // 60}h {weekly_minutes % 60}m"

        # دقة المراجعة
        tr = sum(int(w.get("total_reviews", 0) or 0) for w in words)
        cr = sum(int(w.get("correct_reviews", 0) or 0) for w in words)
        accuracy = f"{int(cr / tr * 100)}%" if tr > 0 else "—"

        self.card_vals[0].config(text=str(total_words))
        self.card_vals[1].config(text=str(today_words))
        self.card_vals[2].config(text=weekly_hours)
        self.card_vals[3].config(text=accuracy)

        # خريطة الحرارة
        for w in self.heatmap.winfo_children():
            w.destroy()

        days = [(date.today() - timedelta(days=6 - i)) for i in range(7)]
        day_names = ["الأحد", "الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت"]
        max_mins = max((db.get_daily_stats(d.isoformat()).get("minutes", 0) for d in days), default=1)

        for d in days:
            mins = db.get_daily_stats(d.isoformat()).get("minutes", 0)
            intensity = max(30, int(mins / max(max_mins, 1) * 255)) if mins > 0 else 20
            color = f"#{0:02x}{intensity:02x}{0:02x}" if mins > 0 else C["surface2"]

            col = tk.Frame(self.heatmap, bg=C["bg"])
            col.pack(side="left", expand=True, fill="x", padx=3)
            box = tk.Frame(col, bg=color, highlightbackground=C["border"], highlightthickness=1)
            box.pack(fill="x")
            tk.Canvas(box, height=44, bg=color, highlightthickness=0).pack()
            tk.Label(col, text=day_names[d.weekday()], bg=C["bg"],
                     fg=C["text3"], font=("Arial", 7)).pack()

        self.after(5000, self._refresh)