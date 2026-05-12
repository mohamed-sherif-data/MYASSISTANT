# services/sound.py
"""
SoundManager مستقل لتشغيل نغمات النظام (Windows).
يمكن استبداله بسهولة لمنصات أخرى.
"""

from __future__ import annotations

import logging
import threading
import time

logger = logging.getLogger(__name__)


class SoundManager:
    """أصوات غير متزامنة (non-blocking) عبر winsound."""

    PATTERNS = {
        "work":     [(800,150),(900,150),(1000,150),(1100,150),(1200,150)],
        "break":    [(1200,150),(1100,150),(1000,150),(900,150),(800,150)],
        "finished": [(1000,200),(0,200),(1000,200),(0,200),(1000,200),
                     (0,200),(1000,200),(0,200),(1000,200)],
        "save":     [(600,100),(800,100),(1000,100)],
        "note":     [(880,300)],
        "error":    [(300,500)],
        "flip":     [(500,80)],
        "correct":  [(800,100),(1000,150)],
        "wrong":    [(400,200)],
        "normal":   [(750,200)],
    }

    def beep(self, pattern: str = "normal") -> None:
        threading.Thread(target=self._play, args=(pattern,), daemon=True).start()

    def _play(self, pattern: str) -> None:
        try:
            import winsound
            for freq, dur in self.PATTERNS.get(pattern, self.PATTERNS["normal"]):
                if freq == 0:
                    time.sleep(dur / 1000)
                else:
                    winsound.Beep(freq, dur)
                    time.sleep(0.04)
        except Exception as e:
            logger.error(f"Sound error: {e}")