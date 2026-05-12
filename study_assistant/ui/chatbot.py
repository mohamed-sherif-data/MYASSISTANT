# ui/chatbot.py
"""
نافذة Chatbot للمحادثة والتمرين.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

from config import C

if TYPE_CHECKING:
    from main import StudyAssistant

from services.chatbot import ChatbotPractice


class ChatbotWindow:
    """نافذة المحادثة."""

    def __init__(self, app: StudyAssistant) -> None:
        self.app = app
        self.chatbot = ChatbotPractice(app.groq, app.db)
        self.messages: list[tuple[str, str]] = []
        self.win: tk.Toplevel | None = None

    def show(self) -> None:
        if self.win and self.win.winfo_exists():
            self.win.lift()
            return

        self.win = tk.Toplevel(self.app.root)
        self.win.title("💬 تمرين بالمحادثة")
        self.win.configure(bg=C["bg"])
        sw, sh = self.win.winfo_screenwidth(), self.win.winfo_screenheight()
        self.win.geometry(f"450x600+{(sw-450)//2}+{(sh-600)//2}")
        self.win.minsize(400, 500)

        # اختيار المادة
        top = tk.Frame(self.win, bg=C["surface"], padx=16, pady=8)
        top.pack(fill="x")
        
        tk.Label(top, text="المادة:", bg=C["surface"], fg=C["text2"],
                font=("Arial", 10)).pack(side="left")
        
        self.subject_var = tk.StringVar(value="الكل")
        subjects = ["الكل"] + sorted({
            w.get("subject", "") for w in self.app.db.load_words() if w.get("subject")
        })
        subj_combo = ttk.Combobox(top, textvariable=self.subject_var, values=subjects,
                             state="readonly", font=("Arial", 10))
        subj_combo.pack(side="left", padx=8)
        subj_combo.bind("<<ComboboxSelected>>", lambda e: self._change_subject())

        # منطقة الرسائل
        self.msg_frame = tk.Frame(self.win, bg=C["bg"])
        self.msg_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.msg_canvas = tk.Canvas(self.msg_frame, bg=C["bg"], highlightthickness=0)
        self.msg_canvas.pack(side="left", fill="both", expand=True)
        self.msg_scroll = ttk.Scrollbar(self.msg_frame, command=self.msg_canvas.yview)
        self.msg_scroll.pack(side="right", fill="y")
        self.msg_canvas.configure(yscrollcommand=self.msg_scroll.set)
        
        self.chat_frame = tk.Frame(self.msg_canvas, bg=C["bg"])
        self.msg_canvas.create_window((0, 0), window=self.chat_frame, anchor="nw")
        self.chat_frame.bind("<Configure>", 
            lambda e: self.msg_canvas.configure(scrollregion=self.msg_canvas.bbox("all")))

        # إدخال الرسالة
        input_frame = tk.Frame(self.win, bg=C["surface"], padx=16, pady=10)
        input_frame.pack(fill="x", side="bottom")
        
        self.input_var = tk.StringVar()
        self.input_entry = tk.Entry(input_frame, textvariable=self.input_var,
                                  bg=C["surface2"], fg=C["text"],
                                  font=("Arial", 11), relief="flat", bd=6)
        self.input_entry.pack(side="left", fill="x", expand=True)
        self.input_entry.bind("<Return>", lambda e: self._send())
        
        tk.Button(input_frame, text="📤", command=self._send,
                 bg=C["primary"], fg="white", font=("Arial", 12),
                 relief="flat", padx=12).pack(side="left", padx=(8, 0))

        # بدء المحادثة
        self._start()

    def _change_subject(self) -> None:
        subj = self.subject_var.get()
        if subj != "الكل":
            self.chatbot.set_subject(subj)

    def _start(self) -> None:
        self._add_message("system", "جاري بدء المحادثة...")
        
        def _get_greeting():
            greeting = self.chatbot.start_conversation()
            self.win.after(0, lambda: self._add_message("bot", greeting))
        
        from threading import Thread
        Thread(target=_get_greeting, daemon=True).start()

    def _send(self) -> None:
        text = self.input_var.get().strip()
        if not text:
            return
        
        self.input_var.set("")
        self._add_message("user", text)
        
        def _get_response():
            response = self.chatbot.respond(text)
            self.win.after(0, lambda: self._add_message("bot", response))
        
        from threading import Thread
        Thread(target=_get_response, daemon=True).start()

    def _add_message(self, sender: str, text: str) -> None:
        if sender == "system":
            color = C["text3"]
            align = "center"
        elif sender == "user":
            color = C["primary"]
            align = "e"
        else:
            color = C["accent"]
            align = "w"
        
        frame = tk.Frame(self.chat_frame, bg=C["bg"])
        frame.pack(fill="x", pady=4, anchor=align)
        
        bg = C["surface"] if sender != "system" else C["surface2"]
        lbl = tk.Label(frame, text=text, bg=bg, fg=color,
                      font=("Arial", 10), wraplength=380,
                      justify="left" if align == "w" else "right",
                      padx=12, pady=8)
        lbl.pack(anchor=align)
        
        self.win.after(10, self._scroll_bottom)

    def _scroll_bottom(self) -> None:
        self.msg_canvas.yview_moveto(1.0)