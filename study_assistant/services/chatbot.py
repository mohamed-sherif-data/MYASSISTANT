# services/chatbot.py
"""
Chatbot للتمرين مع الكلمات المحفوظة.
"""

from __future__ import annotations

import logging
import random
import re

logger = logging.getLogger(__name__)


class ChatbotPractice:
    """Chatbot للمحادثة والتمرين."""

    def __init__(self, groq, db) -> None:
        self.groq = groq
        self.db = db
        self.subject_filter: str = ""

    def set_subject(self, subject: str) -> None:
        """تعيين فلتر المادة."""
        self.subject_filter = subject

    def get_prompt_template(self) -> str:
        """إنشاء قالب للمحادثة."""
        # جلب كلمات المادة المختارة
        words = self.db.load_words()
        
        if self.subject_filter and self.subject_filter != "الكل":
            words = [w for w in words if w.get("subject") == self.subject_filter]
        
        if not words:
            return "لا توجد كلمات محفوظة للممارسة!"
        
        # اختيار 10-15 كلمة عشوائية
        sample = random.sample(words, min(15, len(words)))
        
        words_list = "\n".join([
            f"- {w.get('word')}: {w.get('translation')}"
            for w in sample
        ])
        
        return f"""You are a friendly English tutor helping me practice.
Use only these words in your responses:
{words_list}

Instructions:
1. Ask simple questions using these words
2. Keep responses short (1-2 sentences)
3. If I make mistakes, gently correct me
4. Respond in Arabic but include English words in brackets

Let's start! 👋"""

    def start_conversation(self) -> str:
        """بدء محادثة جديدة."""
        if not self.groq.is_ready:
            return "يرجى إعداد مفتاح GPT أولاً!"
        
        template = self.get_prompt_template()
        
        if template.startswith("لا"):
            return template
        
        try:
            resp = self.groq._call(
                f"{template}\n\nGreet me and ask your first question.",
                timeout=15
            )
            return resp.strip()
        except Exception as e:
            logger.error(f"Chatbot start: {e}")
            return "عذراً، حدث خطأ. تحقق من مفتاح GPT."

    def respond(self, user_input: str) -> str:
        """الرد على رسالة المستخدم."""
        if not self.groq.is_ready or not user_input:
            return ""
        
        try:
            system_prompt = self.get_prompt_template()
            
            resp = self.groq._call(
                f"{system_prompt}\n\nMy response: {user_input}\n\nYour response:",
                timeout=20
            )
            return resp.strip()
        except Exception as e:
            logger.error(f"Chatbot respond: {e}")
            return "عذراً، لم أستطع إنشاء رد. حاول مرة أخرى."

    def check_word_usage(self, text: str) -> list[str]:
        """فحص الكلمات المستخدمة من المحفوظة."""
        words = self.db.load_words()
        
        if self.subject_filter and self.subject_filter != "الكل":
            words = [w for w in words if w.get("subject") == self.subject_filter]
        
        saved_words = {w.get("word", "").lower() for w in words}
        
        # استخراج كلمات المستخدم
        user_words = re.findall(r"\b[a-zA-Z]{2,}\b", text.lower())
        
        # تحديد الكلمات المحفوظة وغير المحفوظة
        used_saved = [w for w in user_words if w in saved_words]
        used_new = [w for w in user_words if w not in saved_words]
        
        return {"saved": used_saved, "new": used_new}