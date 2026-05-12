# -*- coding: utf-8 -*-
"""
core/database.py — طبقة البيانات المركزية (SQLite)
تحل محل DataManager القديم، تدعم كل العمليات السابقة + هجرة اختيارية.
"""

from __future__ import annotations

import json
import logging
import shutil
import sqlite3
import threading
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Callable, Optional
import random

logger = logging.getLogger(__name__)

# ── المسار الافتراضي لقاعدة البيانات ──────────────────────────────────────
DB_PATH = Path(__file__).parent.parent / "data" / "study_assistant.db"
BACKUP_DIR = Path(__file__).parent.parent / "data" / "backups"


class Database:
    """
    مدير قاعدة البيانات المركزي (Singleton-like).
    يُستخدم من كل مكونات التطبيق.
    """

    def __init__(self, db_path: Path | str = DB_PATH) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()  # اتصال منفصل لكل خيط
        self._init_db()
        self._auto_backup()
        self._word_saved_callbacks: list[Callable[[int], None]] = []

    def _auto_backup(self) -> None:
        """نسخة احتياطية يومية من قاعدة البيانات."""
        try:
            today_backup = BACKUP_DIR / f"study_assistant_{date.today().isoformat()}.db"
            if not today_backup.exists() and self.db_path.exists():
                shutil.copy2(self.db_path, today_backup)
                # الاحتفاظ بآخر 7 نسخ فقط
                backups = sorted(BACKUP_DIR.glob("study_assistant_*.db"))
                for old in backups[:-7]:
                    old.unlink()
                logger.info(f"Daily backup created: {today_backup.name}")
        except Exception as e:
            logger.warning(f"Auto backup failed: {e}")

    # ── الاتصال بالخيط الحالي ───────────────────────────────────────────
    @property
    def conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn"):
            self._local.conn = sqlite3.connect(str(self.db_path))
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA foreign_keys=ON")
        return self._local.conn

    def _init_db(self) -> None:
        """تهيئة الجداول إن لم تكن موجودة."""
        conn = self.conn
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS words (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            word            TEXT NOT NULL COLLATE NOCASE,
            translation     TEXT NOT NULL DEFAULT '',
            alt_translations TEXT DEFAULT '[]',
            ipa             TEXT DEFAULT '',
            type            TEXT DEFAULT 'Word',
            level           TEXT DEFAULT 'B1',
            example         TEXT DEFAULT '',
            example_trans   TEXT DEFAULT '',
            related_words   TEXT DEFAULT '[]',
            synonyms        TEXT DEFAULT '[]',
            antonyms        TEXT DEFAULT '[]',
            sound_alikes    TEXT DEFAULT '[]',
            srs_level       INTEGER DEFAULT 0,
            next_review     TEXT NOT NULL,
            total_reviews   INTEGER DEFAULT 0,
            correct_reviews INTEGER DEFAULT 0,
            subject         TEXT DEFAULT '',
            added_date      TEXT NOT NULL,
            UNIQUE(word COLLATE NOCASE)
        );

        CREATE TABLE IF NOT EXISTS daily_stats (
            date        TEXT PRIMARY KEY,
            minutes     INTEGER DEFAULT 0,
            sessions    INTEGER DEFAULT 0,
            words_added INTEGER DEFAULT 0,
            quizzes     INTEGER DEFAULT 0,
            reviews     INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS sessions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            subject     TEXT NOT NULL,
            lecture     INTEGER NOT NULL DEFAULT 1,
            start_time  TEXT NOT NULL,
            end_time    TEXT,
            duration_min INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS review_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            word       TEXT NOT NULL COLLATE NOCASE,
            quality    INTEGER NOT NULL,
            mode       TEXT NOT NULL,
            time_ms    INTEGER DEFAULT 0,
            timestamp  TEXT NOT NULL,
            session_id INTEGER,
            FOREIGN KEY(session_id) REFERENCES sessions(id)
        );
        """)
        conn.commit()

    # ── Observer (keep for compatibility) ─────────────────────────────────
    def on_word_saved(self, callback: Callable[[int], None]) -> None:
        self._word_saved_callbacks.append(callback)

    def _fire_word_saved(self) -> None:
        total = self.count_words()
        for cb in self._word_saved_callbacks:
            try: cb(total)
            except Exception as e: logger.error(f"word_saved cb error: {e}")

    # ══════════════════════════════════════════════════════════════════════
    # الكلمات
    # ══════════════════════════════════════════════════════════════════════
    def add_word(self, entry: dict[str, Any]) -> bool:
        """إضافة كلمة جديدة، ترجع False إن كانت موجودة."""
        try:
            self.conn.execute("""
                INSERT OR IGNORE INTO words
                (word, translation, alt_translations, ipa, type, level,
                 example, example_trans, related_words, synonyms, antonyms,
                 sound_alikes, srs_level, next_review, total_reviews, correct_reviews,
                 subject, added_date)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                entry["Word"], entry["Translation"], entry.get("Alt_Translations","[]"),
                entry.get("IPA",""), entry.get("Type","Word"), entry.get("Level","B1"),
                entry.get("Example",""), entry.get("Example_Translation",""),
                entry.get("Related_Words","[]"), entry.get("Synonyms","[]"),
                entry.get("Antonyms","[]"), entry.get("Sound_Alikes","[]"),
                int(entry.get("SRS_Level",0)), entry.get("Next_Review", date.today().isoformat()),
                int(entry.get("Total_Reviews",0)), int(entry.get("Correct_Reviews",0)),
                entry.get("Subject",""), entry.get("Added_Date", date.today().isoformat())
            ))
            self.conn.commit()
            self._fire_word_saved()
            return True
        except Exception as e:
            logger.error(f"add_word: {e}")
            return False

    def word_exists(self, word: str) -> bool:
        row = self.conn.execute("SELECT 1 FROM words WHERE word=? COLLATE NOCASE", (word,)).fetchone()
        return row is not None

    def delete_word(self, word: str) -> bool:
        try:
            cur = self.conn.execute("DELETE FROM words WHERE word=? COLLATE NOCASE", (word,))
            self.conn.commit()
            return cur.rowcount > 0
        except Exception as e:
            logger.error(f"delete_word: {e}")
            return False

    def update_word(self, word: str, updates: dict[str, Any]) -> None:
        """تحديث حقول معينة لكلمة."""
        allowed_fields = {"translation","alt_translations","ipa","type","level",
                          "example","example_trans","related_words","synonyms","antonyms",
                          "sound_alikes","srs_level","next_review","total_reviews",
                          "correct_reviews","subject","added_date"}
        filtered = {k: v for k, v in updates.items() if k in allowed_fields}
        if not filtered:
            return
        set_clause = ", ".join(f"{k}=?" for k in filtered)
        values = list(filtered.values()) + [word]
        self.conn.execute(f"UPDATE words SET {set_clause} WHERE word=? COLLATE NOCASE", values)
        self.conn.commit()

    def load_words(self, force: bool = False) -> list[dict]:
        """كل الكلمات (بدون cache، يمكن إضافته لاحقاً)."""
        rows = self.conn.execute("SELECT * FROM words ORDER BY added_date DESC").fetchall()
        return [dict(r) for r in rows]

    def count_words(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM words").fetchone()[0]

    def get_due_words(self) -> list[dict]:
        """كلمات مستحقة المراجعة اليوم."""
        today = date.today().isoformat()
        rows = self.conn.execute("""
            SELECT * FROM words
            WHERE srs_level=0 OR next_review <= ?
            ORDER BY srs_level ASC
        """, (today,)).fetchall()
        return [dict(r) for r in rows]

    def get_words_by_subject(self, subject: str) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM words WHERE subject=? ORDER BY added_date DESC", (subject,)).fetchall()
        return [dict(r) for r in rows]

    def search_words(self, query: str) -> list[dict]:
        q = f"%{query}%"
        rows = self.conn.execute(
            "SELECT * FROM words WHERE word LIKE ? OR translation LIKE ? ORDER BY added_date DESC",
            (q, q)
        ).fetchall()
        return [dict(r) for r in rows]

    def update_srs(self, word: str, quality: int) -> None:
        """تحديث SRS بناءً على جودة الإجابة (0-3)."""
        row = self.conn.execute("SELECT srs_level, total_reviews, correct_reviews FROM words WHERE word=? COLLATE NOCASE", (word,)).fetchone()
        if not row:
            return
        srs = row["srs_level"]; total = row["total_reviews"]; correct = row["correct_reviews"]
        total += 1
        if quality == 0:      new_srs = 0
        elif quality == 1:    new_srs = max(0, srs - 1)
        elif quality == 2:    new_srs = min(srs + 1, 6); correct += 1
        else:                 new_srs = min(srs + 2, 6); correct += 1

        intervals = [0,1,3,7,14,30,90]
        days = intervals[new_srs] if new_srs < len(intervals) else 90
        next_review = (date.today() + timedelta(days=days)).isoformat()

        self.update_word(word, {
            "srs_level": new_srs, "next_review": next_review,
            "total_reviews": total, "correct_reviews": correct
        })

    # ══════════════════════════════════════════════════════════════════════
    # الإحصائيات اليومية
    # ══════════════════════════════════════════════════════════════════════
    def _ensure_daily_stat(self, day: str) -> None:
        self.conn.execute("INSERT OR IGNORE INTO daily_stats(date) VALUES (?)", (day,))
        self.conn.commit()

    def log_session(self, minutes: int, subject: str) -> None:
        day = date.today().isoformat()
        self._ensure_daily_stat(day)
        self.conn.execute("UPDATE daily_stats SET minutes=minutes+?, sessions=sessions+1 WHERE date=?",
                          (minutes, day))
        # يمكن تسجيل جلسة منتهية في جدول sessions (اختياري)
        self.conn.commit()

    def log_word_added(self) -> None:
        day = date.today().isoformat()
        self._ensure_daily_stat(day)
        self.conn.execute("UPDATE daily_stats SET words_added=words_added+1 WHERE date=?", (day,))
        self.conn.commit()

    def get_daily_stats(self, day: str) -> dict:
        row = self.conn.execute("SELECT * FROM daily_stats WHERE date=?", (day,)).fetchone()
        return dict(row) if row else {}

    def get_study_minutes_today(self) -> int:
        return self.get_daily_stats(date.today().isoformat()).get("minutes", 0)

    # ══════════════════════════════════════════════════════════════════════
    # الإعدادات (بومودورو، XP، API key، إلخ)
    # ══════════════════════════════════════════════════════════════════════
    def get_setting(self, key: str, default: str = "") -> str:
        row = self.conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        self.conn.execute("INSERT OR REPLACE INTO settings(key, value) VALUES (?,?)", (key, value))
        self.conn.commit()

    def get_json_setting(self, key: str, default: Any = None) -> Any:
        val = self.get_setting(key, "")
        if val:
            try: return json.loads(val)
            except: pass
        return default

    def set_json_setting(self, key: str, data: Any) -> None:
        self.set_setting(key, json.dumps(data, ensure_ascii=False))
    def get_word_of_the_day(self) -> dict | None:
        """كلمة اليوم – تتغير كل يوم، تفضل الكلمات المتقدمة."""
        import hashlib
        words = self.load_words()
        if not words:
            return None
        seed = int(hashlib.md5(date.today().isoformat().encode()).hexdigest(), 16)
        random.seed(seed)
        hard = [w for w in words if w.get("level","") in ("C1","C2","B2")]
        pool = hard if hard else words
        return random.choice(pool)
    # ══════════════════════════════════════════════════════════════════════
    # هجرة من CSV القديم (اختياري، يُستدعى مرة واحدة)
    # ══════════════════════════════════════════════════════════════════════
    def migrate_from_csv(self, csv_path: Path) -> int:
        """هجرة الكلمات من ملف CSV القديم إلى SQLite. تعيد عدد الكلمات المهاجرة."""
        import csv
        if not csv_path.exists():
            logger.warning(f"CSV file not found: {csv_path}")
            return 0
        count = 0
        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if not row.get("Word"):
                        continue
                    word = row["Word"]
                    if self.word_exists(word):
                        continue
                    # تحويل أسماء الحقول القديمة إلى ما يتوافق مع add_word
                    entry = {
                        "Word": word,
                        "Translation": row.get("Translation",""),
                        "Alt_Translations": row.get("Alt_Translations","[]"),
                        "IPA": row.get("IPA",""),
                        "Type": row.get("Type","Word"),
                        "Level": row.get("Level","B1"),
                        "Example": row.get("Example",""),
                        "Example_Translation": row.get("Example_Translation",""),
                        "Related_Words": row.get("Related_Words","[]"),
                        "Synonyms": row.get("Synonyms","[]"),
                        "Antonyms": row.get("Antonyms","[]"),
                        "Sound_Alikes": row.get("Sound_Alikes","[]"),
                        "SRS_Level": row.get("SRS_Level","0"),
                        "Next_Review": row.get("Next_Review", date.today().isoformat()),
                        "Total_Reviews": row.get("Total_Reviews","0"),
                        "Correct_Reviews": row.get("Correct_Reviews","0"),
                        "Subject": row.get("Subject",""),
                        "Added_Date": row.get("Added_Date", date.today().isoformat())
                    }
                    if self.add_word(entry):
                        count += 1
            # استيراد الإحصائيات البسيطة من stats.json إن وجد
            stats_json = Path(csv_path).parent / ".study_stats.json"
            if stats_json.exists():
                stats_data = json.loads(stats_json.read_text(encoding="utf-8"))
                daily = stats_data.get("daily", {})
                for day, data in daily.items():
                    self._ensure_daily_stat(day)
                    self.conn.execute("""
                        UPDATE daily_stats SET minutes=minutes+?, sessions=sessions+?,
                        words_added=words_added+?
                        WHERE date=?""", (data.get("minutes",0), data.get("sessions",0),
                                          data.get("words",0), day))
                self.conn.commit()
            logger.info(f"Migrated {count} words from CSV.")
        except Exception as e:
            logger.error(f"Migration failed: {e}")
        return count

    # ══════════════════════════════════════════════════════════════════════
    # Weakness Detection - تحليل نقاط الضعف
    # ══════════════════════════════════════════════════════════════════════
    def log_review(self, word: str, quality: int, mode: str, time_ms: int = 0) -> None:
        """تسجيل مراجعة لتتبع نقاط الضعف."""
        from datetime import datetime
        try:
            self.conn.execute("""
                INSERT INTO review_history (word, quality, mode, time_ms, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (word, quality, mode, time_ms, datetime.now().isoformat()))
            self.conn.commit()
        except Exception as e:
            logger.error(f"log_review: {e}")

    def get_weakness_analysis(self, days: int = 30) -> dict:
        """تحليل نقاط الضعف خلال فترة معينة."""
        import datetime as dt
        since = (dt.date.today() - dt.timedelta(days=days)).isoformat()
        
        # الأخطاء حسب نوع الاختبار
        mode_errors = self.conn.execute("""
            SELECT mode, COUNT(*) as total,
                   SUM(CASE WHEN quality < 2 THEN 1 ELSE 0 END) as errors
            FROM review_history
            WHERE timestamp >= ? AND quality < 2
            GROUP BY mode
        """, (since,)).fetchall()
        
        # الكلمات الضعيفة (أخطاء متكررة)
        weak_words = self.conn.execute("""
            SELECT word, COUNT(*) as attempts,
                   SUM(CASE WHEN quality < 2 THEN 1 ELSE 0 END) as errors
            FROM review_history
            WHERE timestamp >= ?
            GROUP BY word
            HAVING errors > 1
            ORDER BY errors DESC
            LIMIT 20
        """, (since,)).fetchall()
        
        # الأخطاء حسب المستوى
        level_errors = self.conn.execute("""
            SELECT w.level, COUNT(*) as total,
                   SUM(CASE WHEN rh.quality < 2 THEN 1 ELSE 0 END) as errors
            FROM review_history rh
            JOIN words w ON rh.word = w.word
            WHERE rh.timestamp >= ? AND rh.quality < 2
            GROUP BY w.level
        """, (since,)).fetchall()
        
        # وقت الاستجابة المتوسط
        avg_time = self.conn.execute("""
            SELECT AVG(time_ms) as avg_ms FROM review_history
            WHERE timestamp >= ? AND time_ms > 0
        """, (since,)).fetchone()
        
        # الأخطاء حسب وقت اليوم
        time_errors = self.conn.execute("""
            SELECT 
                CASE 
                    WHEN CAST(strftime('%H', timestamp) AS INT) < 12 THEN 'صباحاً'
                    WHEN CAST(strftime('%H', timestamp) AS INT) < 18 THEN 'ظهراً'
                    ELSE 'مساءً'
                END as period,
                COUNT(*) as total,
                SUM(CASE WHEN quality < 2 THEN 1 ELSE 0 END) as errors
            FROM review_history
            WHERE timestamp >= ?
            GROUP BY period
        """, (since,)).fetchall()
        
        return {
            "mode_errors": {r["mode"]: {"total": r["total"], "errors": r["errors"]} for r in mode_errors},
            "weak_words": [{"word": w["word"], "attempts": w["attempts"], "errors": w["errors"]} for w in weak_words],
            "level_errors": {r["level"]: {"total": r["total"], "errors": r["errors"]} for r in level_errors},
            "avg_time_ms": int(avg_time["avg_ms"] or 0) if avg_time else 0,
            "time_errors": {r["period"]: {"total": r["total"], "errors": r["errors"]} for r in time_errors},
        }

    def get_weakness_report(self) -> str:
        """تقرير نصي مفصل عن نقاط الضعف."""
        analysis = self.get_weakness_analysis(30)
        lines = ["📊 تقرير نقاط الضعف (آخر 30 يوم)", "="*35]
        
        # حسب نوع الاختبار
        if mode_err := analysis.get("mode_errors"):
            lines.append("\n🔸 حسب نوع الاختبار:")
            for mode, data in sorted(mode_err.items(), key=lambda x: x[1]["errors"], reverse=True):
                pct = int(data["errors"]/data["total"]*100) if data["total"] else 0
                if pct > 30:
                    lines.append(f"  ⚠️ {mode}: {pct}% خطأ ({data['errors']}/{data['total']})")
        
        # الكلمات الضعيفة
        if weak := analysis.get("weak_words")[:5]:
            lines.append("\n🔸 كلمات تحتاج مراجعة:")
            for w in weak:
                lines.append(f"  • {w['word']} ({w['errors']} خطأ من {w['attempts']})")
        
        # حسب المستوى
        if lvl_err := analysis.get("level_errors"):
            lines.append("\n🔸 حسب المستوى:")
            for lvl, data in sorted(lvl_err.items(), key=lambda x: x[1]["errors"], reverse=True)[:3]:
                pct = int(data["errors"]/data["total"]*100) if data["total"] else 0
                if pct > 20:
                    lines.append(f"  ⚠️ {lvl}: {pct}% خطأ")
        
        # التوصية
        rec = self._get_recommendation(analysis)
        if rec:
            lines.append(f"\n💡 التوصية: {rec}")
        
        return "\n".join(lines)

    def _get_recommendation(self, analysis: dict) -> str:
        """توليد توصية بناءً على التحليل."""
        mode_err = analysis.get("mode_errors", {})
        lvl_err = analysis.get("level_errors", {})
        
        # إذا لا توجد بيانات، return رسالة افتراضية
        if not mode_err and not lvl_err:
            return "لا توجد بيانات مراجعة كافية بعد"
        
        # إيجاد الأضعف
        try:
            worst_mode = max(mode_err.items(), key=lambda x: x[1]["errors"]/x[1]["total"] if x[1]["total"] else 0)
        except (ValueError, TypeError):
            worst_mode = ("default", {"errors": 0, "total": 0})
        
        try:
            worst_level = max(lvl_err.items(), key=lambda x: x[1]["errors"]/x[1]["total"] if x[1]["total"] else 0)
        except (ValueError, TypeError):
            worst_level = ("default", {"errors": 0, "total": 0})
        
        pct_mode = worst_mode[1]["errors"]/worst_mode[1]["total"]*100 if worst_mode[1]["total"] else 0
        pct_level = worst_level[1]["errors"]/worst_level[1]["total"]*100 if worst_level[1]["total"] else 0
        
        if pct_mode > 40:
            return f"ركّز على مراجعة {worst_mode[0]} أكثر"
        elif pct_level > 30:
            return f"كلمات {worst_level[0]} تحتاج مراجعة أكثر"
        elif analysis.get("avg_time_ms", 0) > 10000:
            return "حاول الإجابة بسرعة أكبر"
        else:
            return "مجهود جيد! continue reviewing"

    def get_adaptive_interval(self, word: str, quality: int) -> int:
        """تحديدفترة المراجعة الذكيّة."""
        intervals = [0,1,3,7,14,30,90]
        
        # الحصول على بيانات الكلمة
        row = self.conn.execute(
            "SELECT srs_level FROM words WHERE word=? COLLATE NOCASE", (word,)
        ).fetchone()
        if not row:
            return intervals[2]
        
        srs = row["srs_level"]
        
        # فحص أنماط الأخطاء المتكررة
        recent = self.conn.execute("""
            SELECT COUNT(*) as cnt FROM review_history
            WHERE word=? COLLATE NOCASE AND quality < 2
            ORDER BY timestamp DESC LIMIT 5
        """, (word,)).fetchone()
        
        recent_errors = recent["cnt"] if recent else 0
        
        # إذا كان هناك أخطاء متكررة، shorten interval
        if recent_errors >= 3:
            new_srs = max(0, srs - 1)
        elif quality == 3:
            new_srs = min(srs + 2, 6)
        elif quality == 2:
            new_srs = min(srs + 1, 6)
        elif quality == 1:
            new_srs = max(0, srs - 1)
        else:
            new_srs = 0
        
        return intervals[new_srs] if new_srs < len(intervals) else 90