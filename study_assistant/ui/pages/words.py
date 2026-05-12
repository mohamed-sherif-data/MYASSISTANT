# ui/pages/words.py
"""
صفحة الكلمات — جدول بكل الكلمات، بحث، حذف، وتفاصيل عند التحديد.
"""

from __future__ import annotations

import json
import tkinter as tk
from tkinter import ttk, messagebox
from typing import TYPE_CHECKING

from config import C, LEVEL_COLORS
from services.tts import HAS_TTS

if TYPE_CHECKING:
    from main import StudyAssistant


class WordsPage(tk.Frame):
    def __init__(self, parent: tk.Widget, app: StudyAssistant) -> None:
        super().__init__(parent, bg=C["bg"])
        self.app = app
        self._build()

    def _build(self) -> None:
        # شريط العنوان
        hdr = tk.Frame(self, bg=C["bg"])
        hdr.pack(fill="x", padx=20, pady=14)
        tk.Label(hdr, text="📋 جميع الكلمات", bg=C["bg"], fg=C["text"],
                 font=("Arial", 15, "bold")).pack(side="left")
        tk.Button(hdr, text="🗑 حذف المحدد",
                  command=self._delete_selected,
                  bg=C["danger"], fg="white", font=("Arial", 9, "bold"),
                  relief="flat", padx=10, pady=4).pack(side="right", padx=6)
        tk.Button(hdr, text="📖_generate_story",
                  command=self._generate_story,
                  bg=C["accent"], fg="white", font=("Arial", 9),
                  relief="flat", padx=10, pady=4).pack(side="right")

        # حقل البحث
        sf = tk.Frame(self, bg=C["bg"])
        sf.pack(fill="x", padx=20, pady=(0, 8))
        tk.Label(sf, text="🔍", bg=C["bg"], fg=C["text2"]).pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *_: self._refresh())
        tk.Entry(sf, textvariable=self.search_var, bg=C["surface2"], fg=C["text"],
                 font=("Arial", 10), relief="flat", insertbackground=C["text"],
                 bd=6).pack(side="left", fill="x", expand=True, padx=8)

        # جدول الكلمات
        self.tree = ttk.Treeview(self, columns=("word","trans","ipa","type","level","srs","syn","added"),
                                 show="headings")
        for col, head, width in [
            ("word", "الكلمة", 110), ("trans", "الترجمة", 140), ("ipa", "IPA", 100),
            ("type", "النوع", 60), ("level", "مستوى", 55), ("srs", "SRS", 40),
            ("syn", "مرادفات", 110), ("added", "أُضيفت", 90)
        ]:
            self.tree.heading(col, text=head)
            self.tree.column(col, width=width, anchor="center")
        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        table_frame = tk.Frame(self, bg=C["bg"])
        table_frame.pack(fill="both", expand=True, padx=20, pady=(0, 6))
        self.tree.pack(side="left", fill="both", expand=True, in_=table_frame)
        vsb.pack(side="right", fill="y", in_=table_frame)
        self.tree.bind("<Double-1>", self._speak_word)
        self.tree.bind("<<TreeviewSelect>>", self._show_detail)

        # لوحة تفاصيل الكلمة
        self.detail = tk.Frame(self, bg=C["card_bg"],
                               highlightbackground=C["border"], highlightthickness=1)
        self.detail.pack(fill="x", padx=20, pady=(0, 10))
        self.detail_lbl = tk.Label(self.detail, text="اختر كلمة لعرض تفاصيلها",
                                   bg=C["card_bg"], fg=C["text3"],
                                   font=("Arial", 9), pady=6)
        self.detail_lbl.pack()

        self._refresh()

    def _refresh(self) -> None:
        words = self.app.db.load_words()
        query = self.search_var.get().lower().strip()
        for row in self.tree.get_children():
            self.tree.delete(row)
        for w in reversed(words):
            if query and query not in w.get("word","").lower() and query not in w.get("translation","").lower():
                continue
            # معالجة المرادفات
            syn_raw = w.get("synonyms","[]")
            syn_list = []
            try:
                syn_data = json.loads(syn_raw)
                syn_list = [s["word"] for s in syn_data[:2] if isinstance(s, dict) and s.get("word")]
            except:
                pass
            syn_str = ", ".join(syn_list) if syn_list else ""
            self.tree.insert("", "end", values=(
                w.get("word",""), w.get("translation",""), w.get("ipa",""),
                w.get("type",""), w.get("level",""),
                "★" * min(int(w.get("srs_level",0) or 0), 6),
                syn_str, w.get("added_date","")
            ))

    def _show_detail(self, event=None) -> None:
        sel = self.tree.selection()
        for wdg in self.detail.winfo_children():
            wdg.destroy()
        if not sel:
            self.detail_lbl = tk.Label(self.detail, text="اختر كلمة لعرض تفاصيلها",
                                       bg=C["card_bg"], fg=C["text3"],
                                       font=("Arial", 9), pady=6)
            self.detail_lbl.pack()
            return
        word = self.tree.item(sel[0], "values")[0]
        words = self.app.db.load_words()
        entry = next((w for w in words if w["word"] == word), None)
        if not entry:
            return

        f = tk.Frame(self.detail, bg=C["card_bg"], padx=12, pady=8)
        f.pack(fill="x")
        # السطر الأول: الكلمة + IPA
        top = tk.Frame(f, bg=C["card_bg"])
        top.pack(fill="x")
        tk.Label(top, text=entry.get("word",""), bg=C["card_bg"], fg=C["text"],
                 font=("Georgia", 16, "bold")).pack(side="left")
        if ipa := entry.get("ipa",""):
            tk.Label(top, text=f"  {ipa}", bg=C["card_bg"], fg=C["text3"],
                     font=("Arial", 10, "italic")).pack(side="left")
        # الترجمات
        trans = entry.get("translation","")
        alts_raw = entry.get("alt_translations","[]")
        alts = []
        try: alts = json.loads(alts_raw)
        except: pass
        all_trans = [trans] + [a for a in alts if a]
        tk.Label(f, text=" →  " + "  |  ".join(all_trans), bg=C["card_bg"],
                 fg=C["green"], font=("Arial", 10), wraplength=550).pack(anchor="w")
        # مثال
        if ex := entry.get("example",""):
            tk.Label(f, text=f'"{ex}"', bg=C["card_bg"], fg=C["text2"],
                     font=("Arial", 9, "italic"), wraplength=550).pack(anchor="w", pady=(4,0))
        # المرادفات والأضداد
        syn_raw = entry.get("synonyms","[]")
        ant_raw = entry.get("antonyms","[]")
        syns, ants = [], []
        try: syns = [s["word"] for s in json.loads(syn_raw)[:3] if isinstance(s,dict) and s.get("word")]
        except: pass
        try: ants = [a["word"] for a in json.loads(ant_raw)[:2] if isinstance(a,dict) and a.get("word")]
        except: pass
        if syns:
            tk.Label(f, text="≈ " + "  •  ".join(syns), bg=C["card_bg"],
                     fg=C["green"], font=("Arial", 9)).pack(anchor="w")
        if ants:
            tk.Label(f, text="≠ " + "  •  ".join(ants), bg=C["card_bg"],
                     fg="#f78166", font=("Arial", 9)).pack(anchor="w")

    def _speak_word(self, event=None) -> None:
        if not HAS_TTS:
            return
        sel = self.tree.selection()
        if sel:
            word = self.tree.item(sel[0], "values")[0]
            self.app.tts.speak_word(word)

    def _delete_selected(self) -> None:
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("تنبيه", "اختر كلمة أولاً")
            return
        word = self.tree.item(sel[0], "values")[0]
        if messagebox.askyesno("حذف كلمة", f'هل تريد حذف "{word}" نهائياً؟'):
            if self.app.db.delete_word(word):
                self.app.sound.beep("normal")
                self._refresh()
                for wdg in self.detail.winfo_children():
                    wdg.destroy()
                self.detail_lbl = tk.Label(self.detail, text="تم الحذف",
                                           bg=C["card_bg"], fg=C["danger"],
                                           font=("Arial", 9), pady=6)
                self.detail_lbl.pack()
            else:
                messagebox.showerror("خطأ", "لم يتم العثور على الكلمة")

    def _generate_story(self) -> None:
        """توليد قصة من كلمات المستخدم."""
        words = self.app.db.load_words()
        if len(words) < 3:
            messagebox.showinfo("تنبيه", "أضف 3 كلمات على الأقل")
            return
        
        # اختيار كلمات عشوائية
        import random
        word_list = [w["word"] for w in words[:50]]
        selected = random.sample(word_list, min(6, len(word_list)))
        
        try:
            story = self.app.sentences.generate_story(selected)
            
            # عرض في نافذة جديدة
            win = tk.Toplevel(self.app.root)
            win.title("📖 قصة من كلماتك")
            win.configure(bg=C["bg"])
            win.geometry("500x400")
            
            f = tk.Frame(win, bg=C["bg"], padx=20, pady=20)
            f.pack(fill="both", expand=True)
            
            tk.Label(f, text="📖 قصة باستخدام كلماتك:", bg=C["bg"], fg=C["text"],
                     font=("Arial", 12, "bold")).pack(pady=(0, 10))
            
            # عرض القصة
            txt = tk.Text(f, bg=C["surface"], fg=C["text"],
                          font=("Consolas", 11), wrap="word",
                          height=12, bd=0)
            txt.pack(fill="both", expand=True)
            txt.insert("1.0", story)
            txt.config(state="disabled")
            
            # زر النسخ
            def copy_story():
                try:
                    import pyperclip
                    pyperclip.copy(story)
                except:
                    pass
            
            tk.Button(f, text="📋 نسخ", command=copy_story,
                      bg=C["surface2"], fg=C["text"],
                      font=("Arial", 10), relief="flat",
                      padx=16, pady=6).pack(pady=10)
            
        except Exception as e:
            messagebox.showerror("خطأ", f"فشل توليد القصة: {e}")