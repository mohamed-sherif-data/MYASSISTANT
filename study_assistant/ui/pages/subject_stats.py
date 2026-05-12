# ui/pages/subject_stats.py
"""
صفحة إحصائيات كل مادة.
"""

from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING

from config import C

if TYPE_CHECKING:
    from main import StudyAssistant


class SubjectStatsPage(tk.Frame):
    """صفحة إحصائيات لكل مادة."""

    def __init__(self, parent: tk.Widget, app: StudyAssistant) -> None:
        super().__init__(parent, bg=C["bg"])
        self.app = app
        self._build()

    def _build(self) -> None:
        tk.Label(self, text="📈 إحصائيات لكل مادة", bg=C["bg"], fg=C["text"],
                 font=("Arial", 15, "bold")).pack(anchor="w", padx=20, pady=16)

        self.stats_frame = tk.Frame(self, bg=C["bg"])
        self.stats_frame.pack(fill="both", expand=True, padx=16, pady=4)

        self._refresh()

    def _refresh(self) -> None:
        """تحديث الإحصائيات."""
        for w in self.stats_frame.winfo_children():
            w.destroy()

        words = self.app.db.load_words()
        
        # تجميع حسب المادة
        subjects: dict = {}
        for w in words:
            subj = w.get("subject", "") or "بدون مادة"
            if subj not in subjects:
                subjects[subj] = {"words": 0, "total_reviews": 0, "correct_reviews": 0, "minutes": 0, "srs_dist": {}}
            subjects[subj]["words"] += 1
            subjects[subj]["total_reviews"] += int(w.get("total_reviews", 0) or 0)
            subjects[subj]["correct_reviews"] += int(w.get("correct_reviews", 0) or 0)
            srs = w.get("srs_level", 0)
            subjects[subj]["srs_dist"][str(srs)] = subjects[subj]["srs_dist"].get(str(srs), 0) + 1

        if not subjects:
            tk.Label(self.stats_frame, text="لا توجد بيانات بعد",
                    bg=C["bg"], fg=C["text3"], font=("Arial", 11)).pack(pady=30)
            return

        colors = [C["blue"], C["green"], C["purple"], C["yellow"],
                  C["accent"], "#f78166", C["warning"]]

        for i, (subj, data) in enumerate(sorted(subjects.items())):
            clr = colors[i % len(colors)]
            card = tk.Frame(self.stats_frame, bg=C["card_bg"],
                          highlightbackground=C["border"], highlightthickness=1)
            card.pack(fill="x", pady=4)

            # رأس
            hdr = tk.Frame(card, bg=clr, padx=12, pady=6)
            hdr.pack(fill="x")
            tk.Label(hdr, text=subj, bg=clr, fg="white",
                   font=("Arial", 11, "bold")).pack(side="left")
            tk.Label(hdr, text=f"{data['words']} كلمة", bg=clr, fg="white",
                   font=("Arial", 9)).pack(side="right")

            # تفاصيل
            det = tk.Frame(card, bg=C["card_bg"], padx=12, pady=8)
            det.pack(fill="x")
            tr = data["total_reviews"]
            cr = data["correct_reviews"]
            acc = f"{int(cr/tr*100)}%" if tr else "—"

            for lbl, val, fg in [
                ("دقة المراجعة", acc, C["green"]),
                ("مراجعات", str(tr), C["text2"]),
            ]:
                r = tk.Frame(det, bg=C["card_bg"])
                r.pack(side="left", padx=12)
                tk.Label(r, text=lbl, bg=C["card_bg"], fg=C["text3"],
                       font=("Arial", 8)).pack()
                tk.Label(r, text=val, bg=C["card_bg"], fg=fg,
                       font=("Consolas", 13, "bold")).pack()

            # SRS توزيع
            srs = data.get("srs_dist", {})
            if srs:
                srs_f = tk.Frame(card, bg=C["card_bg"], padx=12, pady=(0, 8))
                srs_f.pack(fill="x")
                tk.Label(srs_f, text="SRS:", bg=C["card_bg"], fg=C["text3"],
                       font=("Arial", 8)).pack(side="left")
                srs_colors = [C["danger"], C["warning"], C["yellow"],
                             C["blue"], C["green"], C["purple"], C["accent"]]
                for lvl in range(7):
                    cnt = srs.get(str(lvl), 0)
                    if cnt:
                        tk.Label(srs_f, text=f"L{lvl}:{cnt}",
                                bg=C["card_bg"], fg=srs_colors[lvl],
                                font=("Consolas", 8)).pack(side="left", padx=4)

        # تحديث كل 10 ثوانٍ
        self.after(10000, self._refresh)