# services/paragraph_processor.py
"""
معالج الفقرات: استخراج الكلمات + ترجمة الفقرة
."""

from __future__ import annotations

import logging
import re
import threading

logger = logging.getLogger(__name__)


class ParagraphProcessor:
    """معالج الفقرات لاستخراج الكلمات غير المحفوظة."""

    def __init__(self, groq, db) -> None:
        self.groq = groq
        self.db = db

    def process(self, text: str, min_len: int = 3) -> dict:
        """
        معالجة نص كبير:
        1. استخراج الكلمات غير المحفوظة
        2. ترجمة الفقرة كاملة
        
        Returns:
            {
                "words": [{"word": "...", "translation": "..."}],
                "translation": "...",
                "existing_words": [...],
                "new_words": [...],
            }
        """
        result = {
            "words": [],
            "translation": "",
            "existing_words": [],
            "new_words": [],
        }
        
        if not text or len(text.strip()) < 10:
            return result
        
        # استخراج الكلمات الإنجليزية
        words = self._extract_words(text)
        
        # فحص الكلمات الموجودة
        all_words = {w.get("word", "").lower() for w in self.db.load_words()}
        
        for word in words:
            w_lower = word.lower()
            if w_lower in all_words:
                result["existing_words"].append(word)
            else:
                result["new_words"].append(word)
        
        # ترجمة الفقرة (委托 لـ Groq)
        if self.groq.is_ready:
            thread = threading.Thread(
                target=self._translate_async,
                args=(text, result),
                daemon=True
            )
            thread.start()
        else:
            result["translation"] = "GPT key not configured"
        
        return result

    def _extract_words(self, text: str) -> list[str]:
        """استخراج كلمات إنجليزية من النص."""
        # إزالة الأرقام وعلامات الترقيم
        cleaned = re.sub(r"\d+", "", text)
        cleaned = re.sub(r"[^\w\s]", "", cleaned)
        
        # تقسيم لكلمات
        words = re.findall(r"\b[a-zA-Z]{3,}\b", cleaned)
        
        # إزالة الكلمات الشائعة
        stopwords = {
            "the", "and", "for", "are", "but", "not", "you", "all",
            "can", "had", "her", "was", "one", "our", "out", "day",
            "get", "has", "him", "his", "how", "its", "may",
            "new", "now", "old", "see", "two", "way", "who", "boy",
            "did", "isn", "is", "am", "are", "was", "were",
            "have", "has", "had", "doing", "does", "did",
        }
        
        return [w for w in words if w.lower() not in stopwords]

    def _translate_async(self, text: str, result: dict) -> None:
        """ترجمة 비동وية."""
        try:
            prompt = f"""Translate this English paragraph to Arabic. 
Keep the original in brackets after each sentence.

Paragraph:
{text}

Translation:"""

            resp = self.groq._call(prompt, timeout=20)
            result["translation"] = resp.strip()
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            result["translation"] = ""

    def words_only(self, text: str) -> list[dict]:
        """جلب كلمات غير محفوظة فقط (للكتابة في قاعدة البيانات)."""
        words = self._extract_words(text)
        all_words = {w.get("word", "").lower() for w in self.db.load_words()}
        
        new = []
        for w in words:
            if w.lower() not in all_words:
                new.append({"word": w, "translation": ""})
        
        return new