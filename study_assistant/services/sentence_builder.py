# services/sentence_builder.py
"""
AI Sentence Builder - توليد جمل وقصص باستخدام كلمات المستخدم.
"""

from __future__ import annotations
import logging
from typing import Any

logger = logging.getLogger(__name__)


class SentenceBuilder:
    """توليد تمارين بالذكاء الاصطناعي."""

    def __init__(self, groq_client: Any) -> None:
        self.groq = groq_client

    def generate_story(self, words: list[str], lang: str = "ar") -> str:
        """توليد قصة قصيرة باستخدام الكلمات."""
        if not words or not self.groq.is_ready:
            return self._fallback_story(words)

        word_list = ", ".join(words[:8])
        prompt = (
            f"Create a short story (3-5 sentences) in English using these vocabulary words: {word_list}\n"
            "The story should be simple and natural. Then translate it to Arabic.\n"
            "Format:\n"
            "ENGLISH:\n<story in English>\n"
            "ARABIC:\n<translation>"
        )
        try:
            result = self.groq._call(prompt, timeout=20)
            return result
        except Exception as e:
            logger.error(f"Story generation: {e}")
            return self._fallback_story(words)

    def generate_dialogue(self, words: list[str]) -> str:
        """توليد حوار."""
        if not words or not self.groq.is_ready:
            return self._fallback_dialogue(words)

        word_list = ", ".join(words[:6])
        prompt = (
            f"Create a short dialogue (6-8 lines) using these words: {word_list}\n"
            "Format:\n"
            "A: English line\n"
            "B: English line\n"
            "(alternating)"
        )
        try:
            result = self.groq._call(prompt, timeout=15)
            return result
        except Exception as e:
            logger.error(f"Dialogue generation: {e}")
            return self._fallback_dialogue(words)

    def generate_exercises(self, words: list[str], exercise_type: str = "fill_blank") -> str:
        """توليد تمارين."""
        if not words or not self.groq.is_ready:
            return self._fallback_exercises(words, exercise_type)

        word_list = ", ".join(words[:10])
        prompt = (
            f"Create 5 {exercise_type} exercises using these words: {word_list}\n"
            "Format as:\n"
            "1. question\n"
            "2. question\n"
            "..."
        )
        try:
            result = self.groq._call(prompt, timeout=15)
            return result
        except Exception as e:
            logger.error(f"Exercises generation: {e}")
            return self._fallback_exercises(words, exercise_type)

    def _fallback_story(self, words: list[str]) -> str:
        if not words:
            return "لا توجد كلمات"
        return f"استخدم كلمات: {', '.join(words[:5])} dalam جملة"

    def _fallback_dialogue(self, words: list[str]) -> str:
        if not words:
            return "لا توجد كلمات"
        return "A: Hello!\nB: Hi!"

    def _fallback_exercises(self, words: list[str], exercise_type: str) -> str:
        if not words:
            return "لا توجد كلمات"
        return f"1. Complete: She ___ great {words[0]}"