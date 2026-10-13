# -*- coding: utf-8 -*-
"""
المعين للتخطيط اليومي - واجهة PySide6
قاعدة البيانات: school_data.db (SQLite)
التشغيل: python3 main.py
"""
import sys
import sqlite3
from pathlib import Path
from datetime import date
import pandas as pd

import os
import shutil
import subprocess
import platform
import zipfile
from datetime import datetime, time, timedelta
from PySide6.QtGui import QTextDocument
from PySide6.QtPrintSupport import QPrinter

from PySide6.QtCore import Qt, QMarginsF
from PySide6.QtGui import (
    QPageLayout,
    QPageSize,
    QFont,
    QTextDocument,
    QTextCursor,
    QTextBlockFormat,
    QTextCharFormat,
)

from PySide6.QtCore import QDate, QLocale, QStringListModel
from PySide6.QtGui import QAction, QTextOption
from PySide6.QtPrintSupport import QPrintDialog, QPrintPreviewDialog
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QGridLayout, QSplitter, QGroupBox, QLabel, QLineEdit, QComboBox, QSpinBox,
    QDateEdit, QTimeEdit, QTableWidget, QTableWidgetItem, QPushButton,
    QMessageBox, QDialog, QDialogButtonBox, QTextEdit, QHeaderView, QAbstractItemView, QCompleter,
    QMenu, QToolButton
)
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QCalendarWidget
from PySide6.QtGui import QColor, QPainter, QFontDatabase

# ---------------------------------------------------------
2# إدارة المسارات بشكل آمن ودقيق (يعمل مع الكود العادي و PyInstaller)
# ---------------------------------------------------------
if hasattr(sys, '_MEIPASS'):
    BASE_DIR = Path(sys._MEIPASS)
else:
    BASE_DIR = Path(__file__).resolve().parent

# تحديد المسارات المطلوبة للملفات الخارجية
APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "school_data.db"
ICON_PATH = BASE_DIR / "icons" / "icon.ico"
FONTS_DIR = BASE_DIR / "fonts"
TEMPLATE_PATH = BASE_DIR / "template.odt"


class Database:
    def __init__(self, path=DB_PATH):
        self.path = str(path)
        self.init_db()

    def connect(self):
        con = sqlite3.connect(self.path)
        con.execute("PRAGMA foreign_keys=ON")
        return con

    def init_db(self):
        with self.connect() as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS ann_scolaire (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom_annee TEXT NOT NULL DEFAULT '2026-2027',
                nom_ecole TEXT DEFAULT '',
                nom_enseignant TEXT DEFAULT '',
                nom_inspecteur TEXT DEFAULT '',
                grade TEXT DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS day_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                ann_scolaire_id INTEGER NOT NULL,
                UNIQUE(date, ann_scolaire_id),
                FOREIGN KEY(ann_scolaire_id) REFERENCES ann_scolaire(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS hessa (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                classe TEXT DEFAULT '',
                majal TEXT DEFAULT '',
                heure TEXT DEFAULT '',
                time TEXT DEFAULT '',
                wehda_number INTEGER DEFAULT 1,
                hessa_number INTEGER DEFAULT 1,
                namat_taallom TEXT DEFAULT '',
                day_data_id INTEGER NOT NULL,
                FOREIGN KEY(day_data_id) REFERENCES day_data(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS nachat (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                time TEXT DEFAULT '',
                hessa_id INTEGER NOT NULL,
                FOREIGN KEY(hessa_id) REFERENCES hessa(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS nachat_detail (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_name TEXT NOT NULL,
                value_text TEXT DEFAULT '',
                nachat_id INTEGER NOT NULL,
                FOREIGN KEY(nachat_id) REFERENCES nachat(id) ON DELETE CASCADE
            );
            """)
            row = c.execute("SELECT id FROM ann_scolaire ORDER BY id LIMIT 1").fetchone()
            if row:
                self.year_id = row[0]
            else:
                cur = c.execute(
                    "INSERT INTO ann_scolaire(nom_annee) VALUES(?)", ("2026-2027",)
                )
                self.year_id = cur.lastrowid

            # التحقق من إدخال المستويات الستة تلقائياً إذا كان الجدول فارغاً
            levels_count = c.execute("SELECT COUNT(*) FROM levels").fetchone()[0]
            if levels_count == 0:
                default_levels = [
                    ("السنة الأولى",),
                    ("السنة الثانية",),
                    ("السنة الثالثة",),
                    ("السنة الرابعة",),
                    ("السنة الخامسة",),
                    ("السنة السادسة",)
                ]
                c.executemany("INSERT INTO levels (level_name) VALUES (?)", default_levels)

            # التحقق وإدخال المجالات الخمسة الأساسية تلقائياً إذا كان الجدول فارغاً
            domains_count = c.execute("SELECT COUNT(*) FROM domains").fetchone()[0]
            if domains_count == 0:
                default_domains = [
                    ("اللغة العربية",),
                    ("العلوم والتكنولوجيا",),
                    ("التنشئة الاجتماعية",),
                    ("التنشئة الفنية",),
                    ("التنشئة البدنية",)
                ]
                c.executemany("INSERT INTO domains (domain_name) VALUES (?)", default_domains)

            row = c.execute("SELECT id FROM ann_scolaire ORDER BY id LIMIT 1").fetchone()
            if row:
                self.year_id = row[0]
            else:
                cur = c.execute(
                    "INSERT INTO ann_scolaire(nom_annee) VALUES(?)", ("2026-2027",)
                )
                self.year_id = cur.lastrowid

    def get_day_id(self, day):
        with self.connect() as c:
            row = c.execute(
                "SELECT id FROM day_data WHERE date=? AND ann_scolaire_id=?",
                (day, self.year_id)
            ).fetchone()
            if row:
                return row[0]
            cur = c.execute(
                "INSERT INTO day_data(date, ann_scolaire_id) VALUES(?,?)",
                (day, self.year_id)
            )
            return cur.lastrowid

    def lessons(self, day_id):
        with self.connect() as c:
            return c.execute("""SELECT id, hessa_number, classe, majal, heure, time,
                wehda_number, namat_taallom FROM hessa
                WHERE day_data_id=? ORDER BY id ASC""", (day_id,)).fetchall()

    def lesson(self, lesson_id):
        with self.connect() as c:
            return c.execute("""SELECT id, classe, majal, heure, time, wehda_number,
                hessa_number, namat_taallom, day_data_id FROM hessa WHERE id=?""",
                (lesson_id,)).fetchone()

    def save_lesson(self, values, day_id, lesson_id=None):
        with self.connect() as c:
            if lesson_id:
                c.execute("""UPDATE hessa SET classe=?, majal=?, heure=?, time=?,
                    wehda_number=?, hessa_number=?, namat_taallom=? WHERE id=?""",
                    (*values, lesson_id))
            else:
                c.execute("""INSERT INTO hessa(classe,majal,heure,time,wehda_number,
                    hessa_number,namat_taallom,day_data_id) VALUES(?,?,?,?,?,?,?,?)""",
                    (*values, day_id))
                return c.execute("SELECT last_insert_rowid()").fetchone()[0]
        return lesson_id

    def delete_lesson(self, lesson_id):
        with self.connect() as c:
            c.execute("DELETE FROM hessa WHERE id=?", (lesson_id,))

    def activities(self, lesson_id):
        with self.connect() as c:
            return c.execute("SELECT id,title,time FROM nachat WHERE hessa_id=? ORDER BY id",
                             (lesson_id,)).fetchall()

    def save_activity(self, title, time, lesson_id, activity_id=None):
        with self.connect() as c:
            if activity_id:
                c.execute("UPDATE nachat SET title=?,time=? WHERE id=?",
                          (title, time, activity_id))
                return activity_id
            cur = c.execute("INSERT INTO nachat(title,time,hessa_id) VALUES(?,?,?)",
                            (title, time, lesson_id))
            return cur.lastrowid

    def delete_activity(self, activity_id):
        with self.connect() as c:
            c.execute("DELETE FROM nachat WHERE id=?", (activity_id,))

    def details(self, activity_id):
        with self.connect() as c:
            return c.execute("""SELECT id,key_name,value_text FROM nachat_detail
                WHERE nachat_id=? ORDER BY id""", (activity_id,)).fetchall()

    def save_detail(self, key, value, activity_id, detail_id=None):
        with self.connect() as c:
            if detail_id:
                c.execute("UPDATE nachat_detail SET key_name=?,value_text=? WHERE id=?",
                          (key, value, detail_id))
                return detail_id
            cur = c.execute("""INSERT INTO nachat_detail(key_name,value_text,nachat_id)
                VALUES(?,?,?)""", (key, value, activity_id))
            return cur.lastrowid

    def delete_detail(self, detail_id):
        with self.connect() as c:
            c.execute("DELETE FROM nachat_detail WHERE id=?", (detail_id,))

    def school_info(self):
        with self.connect() as c:
            return c.execute("""SELECT nom_annee,nom_ecole,nom_enseignant,nom_inspecteur,grade
                FROM ann_scolaire WHERE id=?""", (self.year_id,)).fetchone()

    def update_school_info(self, values):
        with self.connect() as c:
            c.execute("""UPDATE ann_scolaire SET nom_annee=?,nom_ecole=?,nom_enseignant=?,
                nom_inspecteur=?,grade=? WHERE id=?""", (*values, self.year_id))

    def printable_day(self, day_id):
        with self.connect() as c:
            lessons = c.execute("""SELECT id,hessa_number,classe,majal,heure,time,
                wehda_number,namat_taallom FROM hessa WHERE day_data_id=?
                ORDER BY id ASC""", (day_id,)).fetchall()
            result = []
            for lesson in lessons:
                acts = c.execute("SELECT id,title,time FROM nachat WHERE hessa_id=? ORDER BY id",
                                 (lesson[0],)).fetchall()
                act_result = []
                for act in acts:
                    det = c.execute("""SELECT key_name,value_text FROM nachat_detail
                        WHERE nachat_id=? ORDER BY id""", (act[0],)).fetchall()
                    act_result.append((act[1], act[2], det))
                result.append((lesson, act_result))
            return result

    def get_latest_date(self):
        with self.connect() as c:
            row = c.execute(
                "SELECT date FROM day_data WHERE ann_scolaire_id=? ORDER BY date DESC LIMIT 1",
                (self.year_id,)
            ).fetchone()
            return row[0] if row else None
        
    def cleanup_empty_days(self):
        with self.connect() as c:
            c.execute("""
                DELETE FROM day_data 
                WHERE ann_scolaire_id=? 
                AND id NOT IN (SELECT DISTINCT day_data_id FROM hessa)
            """, (self.year_id,))

    def predict_next_detail_key(self, activity_title, namat_taallom, current_count):
        try:
            with self.connect() as c:
                cursor = c.execute("""
                    SELECT n.id, d.key_name
                    FROM nachat_detail d
                    JOIN nachat n ON d.nachat_id = n.id
                    JOIN hessa h ON n.hessa_id = h.id
                    WHERE n.title = ? AND h.namat_taallom = ?
                    ORDER BY n.id, d.id
                """, (activity_title, namat_taallom))
                rows = cursor.fetchall()
                
                sequences = {}
                for nachat_id, key_name in rows:
                    if nachat_id not in sequences:
                        sequences[nachat_id] = []
                    sequences[nachat_id].append(key_name)
                
                candidates = []
                for seq in sequences.values():
                    if len(seq) > current_count:
                        candidates.append(seq[current_count])
                
                if candidates:
                    from collections import Counter
                    most_common = Counter(candidates).most_common(1)
                    if most_common:
                        return most_common[0][0]
        except Exception as e:
            print(f"Prediction error: {e}")
        return ""


class SchoolDataFormatter:
    def __init__(self, db_name=DB_PATH):
        self.db_name = str(db_name)

    def get_connection(self):
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        return conn

    def normalize_date(self, date_str: str) -> str:
        date_str = date_str.strip()
        formats_to_try = ["%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d", "%d/%m/%Y"]
        for fmt in formats_to_try:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
        return date_str

    def get_formatted_day_text(self, date_str: str) -> str:
        formatted_db_date = self.normalize_date(date_str)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    d.id AS day_id, d.date,
                    a.nom_annee, a.nom_ecole, a.nom_enseignant, a.nom_inspecteur, a.grade
                FROM day_data d
                JOIN ann_scolaire a ON d.ann_scolaire_id = a.id
                WHERE d.date = ?
            """, (formatted_db_date,))
            day_row = cursor.fetchone()

            if not day_row:
                return f"❌ لم يتم العثور على أي بيانات مسجلة للتاريخ: {date_str}"

            date_obj = datetime.strptime(day_row['date'], "%Y-%m-%d")
            days_ar = ["الإثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]
            months_ar = ["جانفي", "فيفري", "مارس", "أفريل", "ماي", "جوان", "جويلية", "أوت", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]
            
            day_name = days_ar[date_obj.weekday()]
            month_name = months_ar[date_obj.month - 1]
            formatted_date_header = f"اليوم : {day_name} {date_obj.day} {month_name} {date_obj.year}"

            lines = []
            lines.append(".ـ" * 60)
            spaces = " " * 30
            lines.append(f"{spaces} 📌 {formatted_date_header}")
            lines.append("ـ." * 60)

            cursor.execute("""
                SELECT id, classe, majal, heure, time, wehda_number, hessa_number, namat_taallom
                FROM hessa
                WHERE day_data_id = ?
                ORDER BY id ASC
            """, (day_row['day_id'],))
            hessa_rows = cursor.fetchall()

            if not hessa_rows:
                lines.append("\n  ⚠️ لا توجد حصص مسجلة لهذا اليوم.")
            else:
                for h_idx, h in enumerate(hessa_rows, 1):
                    lines.append(f"\n📘 الحصة: {h['majal']} | القسم: {h['classe']}")
                    lines.append(f"   ├─ التوقيت: {h['heure']} ({h['time']})")
                    lines.append(f"   ├─ الوحدة عدد: {h['wehda_number']} | الحصة / اليوم / المقطع: {h['hessa_number']} | نمط التعلم: {h['namat_taallom']}")
                    lines.append("   └─ الأنشطة:")

                    cursor.execute("""
                        SELECT id, title, time
                        FROM nachat
                        WHERE hessa_id = ?
                        ORDER BY id ASC
                    """, (h['id'],))
                    nachat_rows = cursor.fetchall()

                    if not nachat_rows:
                        lines.append("      └── (لا توجد أنشطة مسجلة لهذه الحصة)")
                    else:
                        for n_idx, n in enumerate(nachat_rows, 1):
                            lines.append(f"      ├─ 📌 النشاط {n_idx}: {n['title']} (المدة: {n['time']})")
                            cursor.execute("""
                                SELECT key_name, value_text
                                FROM nachat_detail
                                WHERE nachat_id = ?
                                ORDER BY id ASC
                            """, (n['id'],))
                            detail_rows = cursor.fetchall()
                            for d in detail_rows:
                                lines.append(f"      │  ├── {d['key_name']}: {d['value_text']}")

            lines.append("\n" + "ـ." * 60)
            return "\n".join(lines)


class YearImportDialog(QDialog):
    def __init__(self, db, default_year_name="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("تحديد السنة الدراسية للاستيراد")
        self.setMinimumWidth(380)
        self.db = db
        
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        self.combo_years = QComboBox()
        self.combo_years.setEditable(True)
        self.load_existing_years()
        if default_year_name:
            self.combo_years.setCurrentText(default_year_name)
            
        form.addRow("السنة الدراسية المستهدفة:", self.combo_years)
        layout.addLayout(form)
        
        buttons = QDialogButtonBox()
        buttons.addButton("متابعة الاستيراد", QDialogButtonBox.AcceptRole)
        buttons.addButton("إلغاء", QDialogButtonBox.RejectRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def load_existing_years(self):
        try:
            with self.db.connect() as con:
                cursor = con.cursor()
                cursor.execute("SELECT id, nom_annee FROM ann_scolaire")
                rows = cursor.fetchall()
                for row in rows:
                    self.combo_years.addItem(row[1], row[0])
        except Exception as e:
            print(f"Error loading years: {e}")

    def get_selected_year_name(self):
        return self.combo_years.currentText().strip()


class SchoolYearSelectionDialog(QDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.setWindowTitle("اختيار السنة الدراسية للتصدير")
        self.setMinimumWidth(350)
        self.db = db
        
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        self.combo_years = QComboBox()
        self.load_years()
        
        form.addRow("السنة الدراسية:", self.combo_years)
        layout.addLayout(form)
        
        buttons = QDialogButtonBox()
        buttons.addButton("تصدير", QDialogButtonBox.AcceptRole)
        buttons.addButton("إلغاء", QDialogButtonBox.RejectRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def load_years(self):
        try:
            with self.db.connect() as con:
                cursor = con.cursor()
                cursor.execute("SELECT id, nom_annee FROM ann_scolaire")
                rows = cursor.fetchall()
                for row in rows:
                    self.combo_years.addItem(row[1], row[0])
        except Exception as e:
            print(f"Error loading years: {e}")

    def get_selected_year_info(self):
        year_id = self.combo_years.currentData()
        year_name = self.combo_years.currentText()
        return year_id, year_name


class AutoCompletionTextEdit(QTextEdit):
    def __init__(self, db, key_combo, activity_title, parent=None):
        super().__init__(parent)
        self.db = db
        self.key_combo = key_combo
        self.activity_title = activity_title
        self.is_completing = False
        self.setAcceptRichText(False)
        self.textChanged.connect(self.on_text_changed)

    def keyPressEvent(self, event):
        cursor = self.textCursor()
        if event.key() == Qt.Key_Tab:
            if cursor.hasSelection():
                cursor.clearSelection()
                cursor.movePosition(QTextCursor.End)
                self.setTextCursor(cursor)
                event.accept()
                return
        super().keyPressEvent(event)

    def on_text_changed(self):
        if self.is_completing:
            return
        cursor = self.textCursor()
        if cursor.atEnd():
            current_text = self.toPlainText()
            if len(current_text.strip()) < 2:
                return
            match = self.find_match_with_pandas(current_text)
            if match and match.startswith(current_text) and match != current_text:
                self.is_completing = True
                remainder = match[len(current_text):]
                pos = cursor.position()
                self.insertPlainText(remainder)
                cursor.setPosition(pos)
                cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
                self.setTextCursor(cursor)
                self.is_completing = False

    def find_match_with_pandas(self, current_text):
        if not current_text.strip():
            return ""
        key_name = self.key_combo.currentText()
        try:
            # 1. جلب البيانات السابقة باستخدام pandas بناءً على الخاصية ونوع النشاط
            with self.db.connect() as con:
                df = pd.read_sql_query("""
                    SELECT d.value_text 
                    FROM nachat_detail d
                    JOIN nachat n ON d.nachat_id = n.id
                    WHERE d.key_name = ? AND n.title = ? AND COALESCE(d.value_text, '') <> ''
                """, con, params=(key_name, self.activity_title))
            
            # إذا لم توجد بيانات كافية لنفس النشاط، نبحث في نفس الخاصية عموماً
            if df.empty:
                with self.db.connect() as con:
                    df = pd.read_sql_query("""
                        SELECT d.value_text 
                        FROM nachat_detail d
                        WHERE d.key_name = ? AND COALESCE(d.value_text, '') <> ''
                    """, con, params=(key_name,))
            
            if df.empty:
                return ""

            text_series = df['value_text'].astype(str)
            current_stripped = current_text.strip()

            # 2. المطابقة المباشرة للجمل والعبارات (مثال: كتب "المت" فتكتمل إلى "المتعلم")
            matches = text_series[text_series.str.startswith(current_stripped, na=False)]
            if not matches.empty:
                # اختيار الجملة الأكثر تكراراً باستخدام pandas
                most_frequent = matches.value_counts().index[0]
                return most_frequent

            # 3. التحليل الذكي للكلمات المتتابعة (N-grams / Successors)
            # استخراج كافة الكلمات والثنائيات (Bigrams) لتحليل ما يذكر عادة بعد الكلمات
            tokens_list = []
            bigrams = []
            for text in text_series:
                tokens = text.split()
                tokens_list.extend(tokens)
                for i in range(len(tokens) - 1):
                    bigrams.append((tokens[i], tokens[i+1]))

            current_tokens = current_stripped.split()
            if current_tokens:
                last_typed_word = current_tokens[-1]
                
                # أ) إكمال الكلمة الحالية الجزئية (إذا كانت تطابق بداية كلمة مسجلة)
                matching_tokens = [t for t in tokens_list if t.startswith(last_typed_word) and t != last_typed_word]
                if matching_tokens:
                    best_token = pd.Series(matching_tokens).mode().iloc[0]
                    if len(current_tokens) > 1:
                        return " ".join(current_tokens[:-1]) + " " + best_token
                    else:
                        return best_token

                # ب) التنبؤ بالكلمة التالية بناءً على الكلمة السابقة (مثال: إذا كتب "حل" يتم اقتراح "مشكل")
                if len(current_tokens) >= 1:
                    prev_word = current_tokens[-1]
                    next_words = [b[1] for b in bigrams if b[0] == prev_word]
                    if next_words:
                        best_next = pd.Series(next_words).mode().iloc[0]
                        return current_stripped + " " + best_next

        except Exception as e:
            print(f"Pandas Completion error: {e}")
        return ""

class CustomCalendarWidget(QCalendarWidget):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.refresh_recorded_dates()

    def refresh_recorded_dates(self):
        try:
            self.setDateTextFormat(QDate(), QTextCharFormat())
            with self.db.connect() as con:
                cursor = con.cursor()
                cursor.execute("""
                    SELECT DISTINCT d.date 
                    FROM day_data d
                    JOIN hessa h ON h.day_data_id = d.id
                    WHERE d.ann_scolaire_id = ?
                """, (self.year_id if hasattr(self, 'year_id') else self.db.year_id,))
                rows = cursor.fetchall()
                
                fmt = QTextCharFormat()
                fmt.setBackground(QColor("#d4edda"))
                fmt.setForeground(QColor("#155724"))
                
                for row in rows:
                    if row[0]:
                        qd = QDate.fromString(row[0], "yyyy-MM-dd")
                        if qd.isValid():
                            self.setDateTextFormat(qd, fmt)
        except Exception as e:
            print(f"Error loading recorded dates: {e}")


from datetime import datetime, time
from PySide6.QtCore import QTime

class LessonEntryDialog(QDialog):
    def __init__(self, title, df_history, weekday_num=None, default_values=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(520)
        self.df_history = df_history
        self.weekday_num = weekday_num
        self.is_updating = False  # لمنع الحلقات اللانهائية عند التحديث المتبادل
        
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        self.combo_classe = QComboBox()
        self.combo_classe.setEditable(True)
        classes = sorted(df_history['classe'].dropna().unique().tolist()) if df_history is not None and not df_history.empty else []
        self.combo_classe.addItems(classes)
        
        self.combo_majal = QComboBox()
        self.combo_majal.setEditable(True)
        
        self.combo_heure = QComboBox()
        self.combo_heure.setEditable(True)
        self.load_day_specific_heures()

        self.combo_time = QComboBox()
        self.combo_time.setEditable(True)
        self.combo_time.addItems(["30 دقيقة", "45 دقيقة", "60 دقيقة", "90 دقيقة", "120 دقيقة"])
        
        self.spin_wehda = QSpinBox()
        self.spin_wehda.setRange(1, 999)
        self.spin_wehda.setValue(1)
        
        self.spin_hessa = QSpinBox()
        self.spin_hessa.setRange(1, 999)
        self.spin_hessa.setValue(1)
        
        self.combo_namat = QComboBox()
        self.combo_namat.addItems(["منهجي", "إدماج", "تقييم", "دعم وعلاج"])
        self.combo_namat.setCurrentText("منهجي")
        
        form.addRow("القسم", self.combo_classe)
        form.addRow("المجال", self.combo_majal)
        form.addRow("التوقيت (مثال: 08:00-09:00)", self.combo_heure)
        form.addRow("مدة الحصة", self.combo_time)
        form.addRow("الوحدة", self.spin_wehda)
        form.addRow("الحصة", self.spin_hessa)
        form.addRow("نمط التعلم", self.combo_namat)
        
        layout.addLayout(form)
        
        buttons = QDialogButtonBox()
        buttons.addButton("حفظ", QDialogButtonBox.AcceptRole)
        buttons.addButton("إلغاء", QDialogButtonBox.RejectRole)
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        # ربط الأحداث مع الدوال الذكية
        self.combo_classe.currentTextChanged.connect(self.on_classe_changed)
        self.combo_majal.currentTextChanged.connect(self.on_majal_changed)
        self.combo_heure.currentTextChanged.connect(self.on_heure_changed)
        
        if default_values:
            if default_values[0]:
                self.combo_classe.setCurrentText(str(default_values[0]))
            if default_values[1]:
                self.combo_majal.setCurrentText(str(default_values[1]))
            if default_values[2]:
                self.combo_heure.setCurrentText(str(default_values[2]))
            if default_values[3]:
                self.combo_time.setCurrentText(str(default_values[3]))
            if default_values[4]:
                self.spin_wehda.setValue(int(default_values[4] or 1))
            if default_values[5]:
                self.spin_hessa.setValue(int(default_values[5] or 1))
            if default_values[6]:
                self.combo_namat.setCurrentText(str(default_values[6]))
        elif classes:
            self.on_classe_changed(self.combo_classe.currentText())

    def load_day_specific_heures(self):
        """جلب التوقيتات المسجلة سابقاً لنفس يوم الأسبوع (مثل الخميس)"""
        if self.df_history is None or self.df_history.empty or self.weekday_num is None:
            return
        try:
            df = self.df_history.copy()
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
            df['wd'] = df['date'].dt.dayofweek
            df_day = df[df['wd'] == self.weekday_num]
            if not df_day.empty and 'heure' in df_day.columns:
                heures = sorted(df_day['heure'].dropna().unique().tolist())
                self.combo_heure.clear()
                self.combo_heure.addItems(heures)
        except Exception as e:
            print(f"Error loading day specific heures: {e}")

    def on_classe_changed(self, classe_text):
        """حين يتغير القسم، يستخدم Pandas للبحث في قاعدة البيانات عن المجالات والتوقيتات المرتبطة به في ذلك اليوم"""
        if self.is_updating or self.df_history is None or self.df_history.empty:
            return
        self.is_updating = True
        try:
            df = self.df_history.copy()
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
            df['wd'] = df['date'].dt.dayofweek
            
            # فلترة حسب القسم ونفس اليوم
            df_sub = df[(df['classe'] == classe_text) & (df['wd'] == self.weekday_num)]
            if df_sub.empty:
                # إذا لم توجد سجلات لنفس اليوم لهذا القسم، نبحث في القسم عموماً
                df_sub = df[df['classe'] == classe_text]

            if not df_sub.empty:
                majals = sorted(df_sub['majal'].dropna().unique().tolist())
                self.combo_majal.clear()
                self.combo_majal.addItems(majals)

                heures = sorted(df_sub['heure'].dropna().unique().tolist())
                if heures:
                    self.combo_heure.clear()
                    self.combo_heure.addItems(heures)

                times = sorted(df_sub['time'].dropna().unique().tolist())
                if times:
                    self.combo_time.clear()
                    self.combo_time.addItems(times)
        except Exception as e:
            print(f"Error in on_classe_changed: {e}")
        finally:
            self.is_updating = False

    def on_majal_changed(self, majal_text):
        """حين يختار المستخدم المجال، يبحث Pandas عن التوقيت الذي دُرس فيه هذا المجال سابقاً"""
        if self.is_updating or not majal_text.strip() or self.df_history is None or self.df_history.empty:
            return
        self.is_updating = True
        try:
            df = self.df_history.copy()
            classe_text = self.combo_classe.currentText().strip()
            
            # البحث عن التوقيت المرتبط بهذا المجال وهذا القسم
            df_sub = df[(df['majal'] == majal_text) & (df['classe'] == classe_text)]
            if df_sub.empty:
                df_sub = df[df['majal'] == majal_text]

            if not df_sub.empty:
                heures = sorted(df_sub['heure'].dropna().unique().tolist())
                if heures:
                    self.combo_heure.clear()
                    self.combo_heure.addItems(heures)
                    # اختيار التوقيت الأكثر تكراراً (Mode) لهذا المجال
                    mode_heure = df_sub['heure'].mode()
                    if not mode_heure.empty:
                        self.combo_heure.setCurrentText(str(mode_heure.iloc[0]))
        except Exception as e:
            print(f"Error in on_majal_changed: {e}")
        finally:
            self.is_updating = False

    def on_heure_changed(self, heure_text):
        """حين يختار المستخدم التوقيت، يبحث Pandas عن المجال الذي كان يُدَرَّس في هذا التوقيت سابقاً + حساب الفارق الزمني"""
        if self.is_updating or not heure_text.strip():
            return
        
        # 1. حساب الفارق الزمني آلياً
        cleaned_text = heure_text.replace(" ", "").replace("ـ", "-")
        if "-" in cleaned_text:
            parts = cleaned_text.split("-")
            if len(parts) == 2:
                try:
                    t1 = datetime.strptime(parts[0].strip(), "%H:%M")
                    t2 = datetime.strptime(parts[1].strip(), "%H:%M")
                    if t2 >= t1:
                        diff_minutes = int((t2 - t1).total_seconds() / 60)
                        self.combo_time.setCurrentText(f"{diff_minutes} دقيقة")
                except ValueError:
                    pass

        # 2. البحث الذكي عن المجال المرتبط بهذا التوقيت باستخدام Pandas
        if self.df_history is None or self.df_history.empty:
            return
        
        self.is_updating = True
        try:
            df = self.df_history.copy()
            classe_text = self.combo_classe.currentText().strip()
            
            df_sub = df[(df['heure'] == heure_text) & (df['classe'] == classe_text)]
            if df_sub.empty:
                df_sub = df[df['heure'] == heure_text]

            if not df_sub.empty:
                mode_majal = df_sub['majal'].mode()
                if not mode_majal.empty:
                    suggested_majal = str(mode_majal.iloc[0])
                    if self.combo_majal.findText(suggested_majal) >= 0:
                        self.combo_majal.setCurrentText(suggested_majal)
        except Exception as e:
            print(f"Error in on_heure_changed: {e}")
        finally:
            self.is_updating = False

    def validate_and_accept(self):
        """التحقق من صحة التوقيت وأنه محصور بين 07:00 و 17:00"""
        heure_text = self.combo_heure.currentText().strip().replace(" ", "").replace("ـ", "-")
        if "-" in heure_text:
            parts = heure_text.split("-")
            if len(parts) == 2:
                try:
                    t1 = datetime.strptime(parts[0].strip(), "%H:%M").time()
                    t2 = datetime.strptime(parts[1].strip(), "%H:%M").time()
                    
                    work_start = time(7, 0)
                    work_end = time(17, 0)
                    
                    if not (work_start <= t1 <= work_end and work_start <= t2 <= work_end):
                        QMessageBox.warning(
                            self, 
                            "توقيت غير مقبول", 
                            "عذراً، أوقات العمل الرسمية يجب أن تكون محصورة حصراً بين الساعة **07:00** صباحاً و **17:00** مساءً."
                        )
                        return
                    if t2 <= t1:
                        QMessageBox.warning(self, "خطأ في التوقيت", "وقت النهاية يجب أن يكون بعد وقت البداية.")
                        return
                except ValueError:
                    QMessageBox.warning(
                        self, 
                        "توقيت غير صالح", 
                        "صيغة التوقيت غير مقبولة. يرجى إدخال التوقيت بالصيغة الصحيحة (مثال: 08:00-09:30)."
                    )
                    return
        else:
            if heure_text:
                QMessageBox.warning(self, "توقيت غير مقبول", "يرجى كتابة التوقيت بصيغة نطاق صحيح يحتوي على علامة الشارطة (-) مثل 08:00-09:00.")
                return

        self.accept()

    def values(self):
        return [
            self.combo_classe.currentText().strip(),
            self.combo_majal.currentText().strip(),
            self.combo_heure.currentText().strip(),
            self.combo_time.currentText().strip(),
            self.spin_wehda.value(),
            self.spin_hessa.value(),
            self.combo_namat.currentText().strip()
        ]


class EntryDialog(QDialog):
    def __init__(self, title, fields, values=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(450)
        self.widgets = []
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        for label, kind, default in fields:
            if kind == "int":
                w = QSpinBox()
                w.setRange(1, 999)
                w.setValue(int(default or 1))
            elif kind in ["multiline", "plaintext"]:
                w = QTextEdit()
                w.setAcceptRichText(False)
                w.setPlainText(str(default or ""))
                w.setMaximumHeight(100)
            else:
                w = QLineEdit(str(default or ""))
            self.widgets.append(w)
            form.addRow(label, w)
            
        if values:
            for w, value in zip(self.widgets, values):
                if isinstance(w, QSpinBox):
                    w.setValue(int(value or 1))
                elif isinstance(w, QTextEdit):
                    w.setPlainText(str(value or ""))
                else:
                    w.setText(str(value or ""))
                    
        layout.addLayout(form)
        
        buttons = QDialogButtonBox()
        buttons.addButton("حفظ", QDialogButtonBox.AcceptRole)
        buttons.addButton("إلغاء", QDialogButtonBox.RejectRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self):
        result = []
        for w in self.widgets:
            if isinstance(w, QSpinBox):
                result.append(w.value())
            elif isinstance(w, QTextEdit):
                result.append(w.toPlainText().strip())
            else:
                result.append(w.text().strip())
        return result

class DaySelectionDialog(QDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.setWindowTitle("اختيار يوم للتصدير")
        # ⬅️ زيادة العرض والارتفاع لتبدو الأيام والتقويم مريحة وواضحة
        self.setMinimumWidth(480)
        self.setMinimumHeight(520)
        self.db = db
        
        layout = QVBoxLayout(self)
        
        # إضافة عنوان توضيحي
        info_label = QLabel("اختر اليوم المطلوب تصديره من التقويم أدناه:")
        info_label.setStyleSheet("font-weight: bold; color: #2c3e50; font-size: 11px;")
        layout.addWidget(info_label)
        
        # إضافة التقويم المخصص الذي يميز الأيام المسجلة
        self.calendar = CustomCalendarWidget(self.db, self)
        layout.addWidget(self.calendar)

        # ⬅️ ضبط لغة التقويم لتكون العربية (تونس) لضمان ظهور أسماء الأيام والأشهر بالعربية
        arabic_locale = QLocale(QLocale.Arabic, QLocale.Tunisia)
        self.calendar.setLocale(arabic_locale)
        
        # أزرار الحوار (موافق / إلغاء)
        buttons = QDialogButtonBox()
        self.export_btn = buttons.addButton("تصدير الملف", QDialogButtonBox.AcceptRole)
        buttons.addButton("إلغاء", QDialogButtonBox.RejectRole)
        
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_selected_date_str(self):
        # إرجاع التاريخ المختار بصيغة yyyy-MM-dd
        return self.calendar.selectedDate().toString("yyyy-MM-dd")

ACTIVITIES_BY_MAJAL = {
    "اللغة العربية": ["تواصل شفوي", "قراءة", "إنتاج كتابي", "استعمال قواعد اللغة",
                      "محفوظات","وحدة اللغة العربية", "رسم وإملاء", "إملاء", "رسم", "مطالعة", "حوار منظم"],
    "العلوم والتكنولوجيا": ["رياضيات", "إيقاظ علمي", "تربية تكنولوجية"],
    "التنشئة الفنية": ["تربية تشكيلية", "تربية موسيقية"],
    "التنشئة الاجتماعية": ["تربية إسلامية", "هدي قرآني", "عقيدة", "أخلاق", "عبادات"],
    "التنشئة البدنية": ["رياضة"],
}
DETAIL_KEYS_BY_NAMAT = {
    "منهجي": ["المحتوى", "هدف الحصة", "السند الرئيسي","مفهوم صحي أو سكاني","المهارة الحياتية", "القصيدة"],
    "إدماج": ["الكفايات المستهدفة","مفهوم صحي أو سكاني","المهارة الحياتية"],
    "تقييم": ["الأداء المنتظر","مفهوم صحي أو سكاني","المهارة الحياتية"],
    "دعم وعلاج": ["المعايير المستهدفة","مفهوم صحي أو سكاني","المهارة الحياتية"],
}


class ActivityEntryDialog(QDialog):
    def __init__(self, title, majal, db, weekday, values=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.majal = majal or ""
        self.weekday = weekday
        self.setWindowTitle(title)
        self.setMinimumWidth(440)
        form = QFormLayout()
        layout = QVBoxLayout(self)

        self.title_combo = QComboBox()
        self.title_combo.setEditable(True)
        self.title_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.title_combo.addItems(ACTIVITIES_BY_MAJAL.get(self.majal, []))
        self.title_combo.setCurrentText(values[0] if values else "")
        self.time_combo = QComboBox()
        self.time_combo.setEditable(True)
        self.time_combo.addItems(["5 دقائق", "10 دقائق", "15 دقيقة", "20 دقيقة",
                                  "30 دقيقة", "45 دقيقة", "60 دقيقة"])
        if not values:
            self.time_combo.setCurrentText("")
        form.addRow("عنوان النشاط", self.title_combo)
        form.addRow("المدة", self.time_combo)
        layout.addLayout(form)
        
        buttons = QDialogButtonBox()
        buttons.addButton("حفظ", QDialogButtonBox.AcceptRole)
        buttons.addButton("إلغاء", QDialogButtonBox.RejectRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.title_combo.currentTextChanged.connect(self.update_duration_suggestion)
        if values:
            self.time_combo.setCurrentText(str(values[1] or ""))
        self.update_duration_suggestion(self.title_combo.currentText())

    def update_duration_suggestion(self, activity_title):
        if not activity_title.strip():
            return
        try:
            with self.db.connect() as con:
                df = pd.read_sql_query("""
                    SELECT n.time, d.date
                    FROM nachat n
                    JOIN hessa h ON h.id = n.hessa_id
                    JOIN day_data d ON d.id = h.day_data_id
                    WHERE n.title = ? AND h.majal = ?
                      AND COALESCE(n.time, '') <> ''
                """, con, params=(activity_title.strip(), self.majal))
            if df.empty:
                return
            dates = pd.to_datetime(df["date"], errors="coerce")
            df = df.loc[dates.dt.dayofweek == self.weekday].copy()
            if df.empty:
                return
            modes = df["time"].astype(str).mode()
            if not modes.empty:
                suggestion = modes.iloc[0]
                old = self.time_combo.currentText()
                if not old or old not in df["time"].astype(str).unique():
                    self.time_combo.setCurrentText(suggestion)
        except Exception as exc:
            print(f"Activity duration prediction error: {exc}")

    def values(self):
        return [self.title_combo.currentText().strip(),
                self.time_combo.currentText().strip()]


class DetailEntryDialog(QDialog):
    def __init__(self, title, namat, activity_title, db, current_count=0, values=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(540)
        self.db = db
        self.namat = namat or ""
        self.activity_title = activity_title or ""
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.key_combo = QComboBox()
        self.key_combo.setEditable(False)
        self.key_combo.addItems(DETAIL_KEYS_BY_NAMAT.get(self.namat, []))
        
        if not values and self.activity_title:
            predicted_key = self.db.predict_next_detail_key(self.activity_title, self.namat, current_count)
            if predicted_key:
                idx = self.key_combo.findText(predicted_key)
                if idx >= 0:
                    self.key_combo.setCurrentIndex(idx)

        self.value_edit = AutoCompletionTextEdit(self.db, self.key_combo, self.activity_title)
        self.value_edit.setPlaceholderText("أدخل قيمة الخاصية هنا… ابدأ الكتابة للاقتراح والتثبيت بـ Tab...")
        
        font_metrics = self.value_edit.fontMetrics()
        self.value_edit.setFixedHeight(font_metrics.lineSpacing() * 5 + 12)

        form.addRow("اسم الخاصية", self.key_combo)
        form.addRow("القيمة", self.value_edit)
        layout.addLayout(form)

        buttons = QDialogButtonBox()
        buttons.addButton("حفظ", QDialogButtonBox.AcceptRole)
        buttons.addButton("إلغاء", QDialogButtonBox.RejectRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if values:
            old_key, old_value = values
            index = self.key_combo.findText(str(old_key or ""))
            if index >= 0:
                self.key_combo.setCurrentIndex(index)
            self.value_edit.setPlainText(str(old_value or ""))

    def values(self):
        return [self.key_combo.currentText().strip(), self.value_edit.toPlainText().strip()]


from PySide6.QtWidgets import QStackedWidget

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

class SchoolPlanner(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = Database(DB_PATH)
        self.day_id = None
        self.selected_lesson_id = None
        self.selected_activity_id = None
        self.copied_details = []
        self.copied_lessons = []
        
        self.setWindowTitle("المعين للتخطيط اليومي للحصص")
        if ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(ICON_PATH)))
            
        self.resize(1250, 800)
        self.setLayoutDirection(Qt.RightToLeft)
        self.build_ui()
        self.load_school_info()

        self.db.cleanup_empty_days()
        latest_date_str = self.db.get_latest_date()
        if latest_date_str:
            qd = QDate.fromString(latest_date_str, "yyyy-MM-dd")
            if qd.isValid():
                self.date_edit.setDate(qd)
        
        self.load_day()
        self.load_statistics() # استدعاء الإحصائيات عند بدء التشغيل
        self.setStyleSheet("QLineEdit { qproperty-alignment: AlignCenter; }")
        self.showMaximized()
        self.setAcceptDrops(True)

    def build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        # ==========================================
        # 1. إعداد مكونات دفتر إعداد الدروس (الصفحة الافتتاحية)
        # ==========================================
        self.school_box = QGroupBox("بيانات المعلم")
        school_grid = QGridLayout(self.school_box)
        self.year_edit = QLineEdit("2026-2027")
        self.school_edit = QLineEdit()
        self.teacher_edit = QLineEdit()
        self.inspector_edit = QLineEdit()
        self.grade_edit = QLineEdit()
        for i, (label, widget) in enumerate([
            ("السنة الدراسية", self.year_edit), ("المؤسسة", self.school_edit),
            ("المعلم", self.teacher_edit), ("المتفقد", self.inspector_edit),
            ("الرتبة", self.grade_edit)
        ]):
            school_grid.addWidget(QLabel(label), 0, i)
            school_grid.addWidget(widget, 1, i)
        self.save_info_btn = QPushButton("حفظ البيانات")
        self.save_info_btn.clicked.connect(self.save_school_info)
        school_grid.addWidget(self.save_info_btn, 1, 5)
        self.school_box.setVisible(False)

        agenda = QGroupBox("الأجندة — اختر اليوم الدراسي")
        agenda_row = QHBoxLayout(agenda)
        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dddd، dd/MM/yyyy")
        self.date_edit.setLocale(QLocale(QLocale.Arabic, QLocale.Tunisia))
        self.date_edit.setMinimumWidth(190)
        
        self.custom_calendar = CustomCalendarWidget(self.db, self.date_edit)
        self.date_edit.setCalendarWidget(self.custom_calendar)
        self.date_edit.dateChanged.connect(self.load_day)
        agenda_row.addWidget(QLabel("اليوم:"))
        agenda_row.addWidget(self.date_edit)
        self.day_status = QLabel()
        agenda_row.addWidget(self.day_status, 1)
        self.prev_btn = QPushButton("◀ اليوم السابق")
        self.next_btn = QPushButton("اليوم التالي ▶")
        self.prev_btn.clicked.connect(lambda: self.date_edit.setDate(self.date_edit.date().addDays(-1)))
        self.next_btn.clicked.connect(lambda: self.date_edit.setDate(self.date_edit.date().addDays(1)))
        agenda_row.addWidget(self.prev_btn)
        agenda_row.addWidget(self.next_btn)

        splitter = QSplitter(Qt.Vertical)

        lesson_box = QGroupBox("الحصص — اختر حصة أو أكثر لإدارة أنشطتها")
        lesson_layout = QVBoxLayout(lesson_box)
        lesson_buttons = QHBoxLayout()
        
        for label, callback, act_type in [
            ("＋ إضافة حصة", self.add_lesson, "add"), 
            ("✎ تعديل الحصة", self.edit_lesson,"edit"),
            ("－ حذف الحصة", self.delete_lesson,"delete"),
            ("📋 نسخ الحصة", self.copy_selected_lessons, "copy_paste"),
            ("📌 لصق الحصة", self.paste_lessons, "copy_paste"),
            ("🗑 مسح حصص اليوم", self.clear_current_day_lessons,"clear"),
            ("⚠️ مسح الكل (كل الأيام)", self.clear_all_lessons_in_db,"clear")
        ]:
            b = QPushButton(label)
            b.clicked.connect(callback)
            b.setProperty("actionType", act_type)
            lesson_buttons.addWidget(b)
            
        lesson_layout.addLayout(lesson_buttons)
        self.lesson_table = self.make_table(
            ["المعرّف", " الحصة", "القسم", "المجال ", "التوقيت",
             "المدة", " الوحدة", "نمط التعلم"]
        )
        self.lesson_table.setColumnHidden(0, True)
        self.lesson_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.lesson_table.itemSelectionChanged.connect(self.on_lesson_selected)
        lesson_layout.addWidget(self.lesson_table)
        splitter.addWidget(lesson_box)

        lower = QSplitter(Qt.Horizontal)
        splitter.addWidget(lower)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)

        act_box = QGroupBox("أنشطة الحصة المحددة")
        act_layout = QVBoxLayout(act_box)
        act_buttons = QHBoxLayout()
        
        for label, callback, act_type in [
            ("＋ إضافة نشاط", self.add_activity,"add"), 
            ("✎ تعديل النشاط", self.edit_activity, "edit"),
            ("－ حذف النشاط", self.delete_activity, "delete"),
            ("🗑 مسح كل الأنشطة", self.clear_all_activities_for_lesson, "clear")
        ]:
            b = QPushButton(label)
            b.clicked.connect(callback)
            b.setProperty("actionType", act_type)
            act_buttons.addWidget(b)
            
        act_layout.addLayout(act_buttons)
        self.activity_table = self.make_table(["المعرّف", "عنوان النشاط", "المدة"])
        self.activity_table.setColumnHidden(0, True)
        self.activity_table.itemSelectionChanged.connect(self.on_activity_selected)
        act_layout.addWidget(self.activity_table)
        
        self.activity_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.activity_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.activity_table.setColumnWidth(2, 90)
        
        lower.addWidget(act_box)

        detail_box = QGroupBox("خصائص النشاط المحدد (اسم الخاصية / قيمتها)")
        detail_layout = QVBoxLayout(detail_box)
        detail_buttons = QHBoxLayout()
        
        for label, callback, act_type in [
            ("＋ إضافة خاصية", self.add_detail, "add"), 
            ("✎ تعديل الخاصية", self.edit_detail, "edit"),
            ("－ حذف الخاصية", self.delete_detail, "delete"),
            ("📋 نسخ الخصائص", self.copy_activity_details, "copy_paste"),
            ("📌 لصق الخصائص", self.paste_activity_details, "copy_paste"),
            ("🗑 مسح كل الخصائص", self.clear_all_details_for_activity, "clear")
        ]:
            b = QPushButton(label)
            b.clicked.connect(callback)
            b.setProperty("actionType", act_type)
            detail_buttons.addWidget(b)
            
        detail_layout.addLayout(detail_buttons)
        self.detail_table = self.make_table(["المعرّف", "اسم الخاصية", "القيمة"])
        self.detail_table.setColumnHidden(0, True)
        detail_layout.addWidget(self.detail_table)
        
        self.detail_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
        self.detail_table.setColumnWidth(1, 150)
        self.detail_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        
        lower.addWidget(detail_box)
        lower.setSizes([600, 600])
        splitter.setSizes([370, 500])

        # ==========================================
        # 2. إعداد صفحة الإحصائيات (menu احصائيات)
        # ==========================================
        self.stats_page = QWidget()
        stats_layout = QVBoxLayout(self.stats_page)
        
        stats_header_layout = QHBoxLayout()
        stats_title = QLabel("📊 لوحة الإحصائيات والتحليلات العامة للدروس")
        stats_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50;")
        self.refresh_stats_btn = QPushButton("🔄 تحديث الإحصائيات")
        self.refresh_stats_btn.clicked.connect(self.load_statistics)
        stats_header_layout.addWidget(stats_title)
        stats_header_layout.addStretch()
        stats_header_layout.addWidget(self.refresh_stats_btn)
        stats_layout.addLayout(stats_header_layout)

        cards_layout = QHBoxLayout()
        self.stat_card_days = QLabel("الأيام المسجلة: 0")
        self.stat_card_lessons = QLabel("إجمالي الحصص: 0")
        self.stat_card_classes = QLabel("الأقسام المسجلة: 0")
        for card in [self.stat_card_days, self.stat_card_lessons, self.stat_card_classes]:
            card.setStyleSheet("""
                background-color: #f8f9fa;
                border: 2px solid #e9ecef;
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
                font-weight: bold;
                color: #495057;
                qproperty-alignment: AlignCenter;
            """)
            cards_layout.addWidget(card)
        stats_layout.addLayout(cards_layout)

        stats_splitter = QSplitter(Qt.Horizontal)
        self.stats_table = self.make_table(["المجال / المادة التعليمية", "عدد الحصص", "النسبة المئوية"])
        stats_splitter.addWidget(self.stats_table)

        try:
            self.fig, self.ax = plt.subplots(figsize=(6, 4))
            self.canvas = FigureCanvas(self.fig)
            stats_splitter.addWidget(self.canvas)
        except Exception as e:
            stats_splitter.addWidget(QLabel(f"تعذر تحميل المخطط البياني: {e}"))

        stats_splitter.setSizes([450, 550])
        stats_layout.addWidget(stats_splitter, 1)

        # ==========================================
        # 3. إعداد صفحة البرامج الرسمية (تصميم عصري متكامل مع أزرار التحكم)
        # ==========================================
        self.official_programs_page = QWidget()
        prog_layout = QVBoxLayout(self.official_programs_page)
        
        # أ) شريط العنوان والفلاتر (المستوى والمجال)
        prog_top_layout = QHBoxLayout()
        prog_title = QLabel("📚 تصفح وإدارة البرامج الرسمية والمستويات والمجالات")
        prog_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50;")
        
        self.combo_prog_level = QComboBox()
        self.combo_prog_level.setMinimumWidth(150)
        self.combo_prog_level.currentIndexChanged.connect(self.load_official_programs)
        
        self.combo_prog_domain = QComboBox()
        self.combo_prog_domain.setMinimumWidth(180)
        self.combo_prog_domain.currentIndexChanged.connect(self.load_official_programs)
        
        prog_top_layout.addWidget(prog_title)
        prog_top_layout.addStretch()
        prog_top_layout.addWidget(QLabel("المستوى:"))
        prog_top_layout.addWidget(self.combo_prog_level)
        prog_top_layout.addWidget(QLabel("المجال:"))
        prog_top_layout.addWidget(self.combo_prog_domain)
        prog_layout.addLayout(prog_top_layout)

        # ب) شريط أزرار التحكم المتقدمة (إضافة، تعديل، مسح، بحث)
        prog_actions_layout = QHBoxLayout()
        
        self.btn_add_level = QPushButton("🏫 إضافة مستوى")
        self.btn_add_domain = QPushButton("📂 إضافة مجال")
        self.btn_add_program = QPushButton("＋ إضافة برنامج / هدف")
        self.btn_edit_program = QPushButton("✎ تعديل المحدد")
        self.btn_delete_program = QPushButton("－ حذف المحدد")
        self.btn_refresh_programs = QPushButton("🔄 تحديث")

        # ربط الأزرار بدوال أو وظائف مبدئية (يمكن تخصيصها لاحقاً حسب رغبتك)
        self.btn_refresh_programs.clicked.connect(self.init_official_programs_filters)

        for btn in [self.btn_add_level, self.btn_add_domain, self.btn_add_program, 
                    self.btn_edit_program, self.btn_delete_program, self.btn_refresh_programs]:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #f8f9fa;
                    border: 1px solid #ced4da;
                    border-radius: 5px;
                    padding: 6px 12px;
                    font-weight: bold;
                    color: #2c3e50;
                }
                QPushButton:hover {
                    background-color: #e2e6ea;
                    border-color: #adb5bd;
                }
            """)
            prog_actions_layout.addWidget(btn)

        prog_actions_layout.addStretch()

        # حقل البحث الفوري المتقدم
        self.search_prog_input = QLineEdit()
        self.search_prog_input.setPlaceholderText("🔍 ابحث في البرامج، المحتويات، أو الأهداف...")
        self.search_prog_input.setMinimumWidth(250)
        # يمكنك ربط حقل البحث بدالة تصفية الجدول مباشرة:
        # self.search_prog_input.textChanged.connect(self.filter_official_programs)
        prog_actions_layout.addWidget(self.search_prog_input)

        prog_layout.addLayout(prog_actions_layout)

        # ج) جدول عرض البيانات
        self.prog_table = self.make_table([
            "المستوى", "المجال", "المادة / الكفاية", 
            "مكون الكفاية", "الهدف النوعي", "المحتوى والتفاصيل"
        ])
        prog_layout.addWidget(self.prog_table, 1)

        # ==========================================
        # 4. تجميع الصفحات داخل QStackedWidget
        # ==========================================
        self.pages_stack = QStackedWidget()
        
        self.lesson_page = QWidget()
        lesson_page_layout = QVBoxLayout(self.lesson_page)
        lesson_page_layout.addWidget(self.school_box)
        lesson_page_layout.addWidget(agenda)
        lesson_page_layout.addWidget(splitter, 1)
        self.pages_stack.addWidget(self.lesson_page)

        self.pages_stack.addWidget(self.stats_page)
        self.pages_stack.addWidget(self.official_programs_page)

        self.plans_page = QWidget()
        plans_layout = QVBoxLayout(self.plans_page)
        plans_layout.addWidget(QLabel("صفحة المخططات — أضف مكوناتها هنا."))
        self.pages_stack.addWidget(self.plans_page)

        self.assessment_page = QWidget()
        assessment_layout = QVBoxLayout(self.assessment_page)
        assessment_layout.addWidget(QLabel("صفحة دفتر التقييم والمتابعة — أضف مكوناتها هنا."))
        self.pages_stack.addWidget(self.assessment_page)

        root.addWidget(self.pages_stack, 1)

        footer = QHBoxLayout()
        self.export_hint = QLabel("تُحفظ التغييرات مباشرة في قاعدة بيانات SQLite.")
        footer.addWidget(self.export_hint, 1)

        self.statusBar().showMessage(f"قاعدة البيانات: {DB_PATH}")
        toolbar = self.addToolBar("ملف")

        # ==========================================
        # 5. إعداد أزرار وقوائم شريط الأدوات (Toolbar)
        # ==========================================
        
        # قائمة دفتر إعداد الدروس
        lesson_book_menu = QMenu("دفتر إعداد الدروس", self)
        
        open_lesson_action = QAction("فتح دفتر إعداد الدروس", self)
        open_lesson_action.triggered.connect(lambda: self.pages_stack.setCurrentWidget(self.lesson_page))
        lesson_book_menu.addAction(open_lesson_action)
        lesson_book_menu.addSeparator()

        toggle_action = QAction("بيانات المعلم", self)
        toggle_action.triggered.connect(self.toggle_enseig_info)

        export_odt_action = QAction("تصدير إلى ملف PDF", self)
        export_odt_action.triggered.connect(self.export_odt_from_db_dialog)

        export_json_action = QAction("تصدير يوم", self)
        export_json_action.triggered.connect(self.export_day_to_json)

        import_json_action = QAction("استيراد يوم", self)
        import_json_action.triggered.connect(self.import_day_from_json)

        export_year_action = QAction("تصدير سنة دراسية كاملة (JSON)", self)
        export_year_action.triggered.connect(self.export_all_days_for_year)

        import_year_action = QAction("استيراد سنة دراسية كاملة (JSON)", self)
        import_year_action.triggered.connect(self.import_all_years_from_json)

        lesson_book_menu.addAction(toggle_action)
        lesson_book_menu.addSeparator()
        lesson_book_menu.addAction(export_odt_action)
        lesson_book_menu.addSeparator()
        lesson_book_menu.addAction(export_json_action)
        lesson_book_menu.addAction(import_json_action)
        lesson_book_menu.addSeparator()
        lesson_book_menu.addAction(export_year_action)
        lesson_book_menu.addAction(import_year_action)

        lesson_book_button = QToolButton(self)
        lesson_book_button.setText("دفتر إعداد الدروس")
        lesson_book_button.setMenu(lesson_book_menu)
        lesson_book_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        toolbar.addWidget(lesson_book_button)

        # قائمة البرامج الرسمية
        programs_menu = QMenu("البرامج الرسمية", self)
        programs_action = QAction("تصفح البرامج الرسمية والجداول", self)
        programs_action.triggered.connect(lambda: {
            self.pages_stack.setCurrentWidget(self.official_programs_page),
            self.init_official_programs_filters()
        })
        programs_menu.addAction(programs_action)
        
        programs_button = QToolButton(self)
        programs_button.setText("البرامج الرسمية")
        programs_button.setMenu(programs_menu)
        programs_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        toolbar.addWidget(programs_button)

        # قائمة إحصائيات
        stats_menu = QMenu("إحصائيات", self)
        stats_action = QAction("فتح لوحة الإحصائيات", self)
        stats_action.triggered.connect(lambda: {
            self.pages_stack.setCurrentWidget(self.stats_page),
            self.load_statistics()
        })
        stats_menu.addAction(stats_action)
        stats_button = QToolButton(self)
        stats_button.setText("إحصائيات")
        stats_button.setMenu(stats_menu)
        stats_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        toolbar.addWidget(stats_button)

        # قائمة المخططات
        plans_menu = QMenu("المخططات", self)
        plans_action = QAction("فتح المخططات", self)
        plans_action.triggered.connect(lambda: self.pages_stack.setCurrentWidget(self.plans_page))
        plans_menu.addAction(plans_action)
        plans_button = QToolButton(self)
        plans_button.setText("المخططات")
        plans_button.setMenu(plans_menu)
        plans_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        toolbar.addWidget(plans_button)

        # قائمة دفتر التقييم والمتابعة
        assessment_menu = QMenu("دفتر التقييم والمتابعة", self)
        assessment_action = QAction("فتح دفتر التقييم والمتابعة", self)
        assessment_action.triggered.connect(lambda: self.pages_stack.setCurrentWidget(self.assessment_page))
        assessment_menu.addAction(assessment_action)
        assessment_button = QToolButton(self)
        assessment_button.setText("دفتر التقييم والمتابعة")
        assessment_button.setMenu(assessment_menu)
        assessment_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        toolbar.addWidget(assessment_button)

    def init_official_programs_filters(self):
        """تهيئة القوائم المنسدلة للمستويات والمجالات بناءً على قاعدة البيانات"""
        try:
            with self.db.connect() as con:
                # تعبئة المستويات (Levels)
                self.combo_prog_level.blockSignals(True)
                self.combo_prog_level.clear()
                self.combo_prog_level.addItem("جميع المستويات", None)
                levels = con.execute("SELECT level_id, level_name FROM levels").fetchall()
                for lid, lname in levels:
                    self.combo_prog_level.addItem(lname, lid)
                self.combo_prog_level.blockSignals(False)

                # تعبئة المجالات (Domains)
                self.combo_prog_domain.blockSignals(True)
                self.combo_prog_domain.clear()
                self.combo_prog_domain.addItem("جميع المجالات", None)
                domains = con.execute("SELECT domain_id, domain_name FROM domains").fetchall()
                for did, dname in domains:
                    self.combo_prog_domain.addItem(dname, did)
                self.combo_prog_domain.blockSignals(False)

            self.load_official_programs()
        except Exception as e:
            print(f"Error initializing program filters: {e}")

    def load_official_programs(self):
        """جلب وعرض البرامج الرسمية والكفايات والأهداف والمحتويات بحسب الفلاتر المحددة"""
        level_id = self.combo_prog_level.currentData()
        domain_id = self.combo_prog_domain.currentData()

        query = """
            SELECT 
                l.level_name, 
                d.domain_name, 
                mc.matier_name, 
                cc.component_text, 
                os.objective_text, 
                c.content_details
            FROM contents c
            JOIN objectives_specifique os ON c.objective_id = os.objective_id
            JOIN levels l ON os.level_id = l.level_id
            JOIN competency_components cc ON os.component_id = cc.component_id
            JOIN material_competencies mc ON cc.material_comp_id = mc.material_comp_id
            JOIN domains d ON mc.domain_id = d.domain_id
            WHERE 1=1
        """
        params = []
        if level_id is not None:
            query += " AND os.level_id = ?"
            params.append(level_id)
        if domain_id is not None:
            query += " AND mc.domain_id = ?"
            params.append(domain_id)

        try:
            with self.db.connect() as con:
                rows = con.execute(query, params).fetchall()
                self.fill_table(self.prog_table, rows)
        except Exception as e:
            print(f"Error loading official programs data: {e}")
    
    def load_statistics(self):
        try:
            # ربط المخطط البياني بخط التطبيق والخطوط الداعمة للغة العربية
            app_font = load_custom_font()
            plt.rcParams['font.family'] = 'sans-serif'
            plt.rcParams['font.sans-serif'] = [app_font, 'Noto Naskh Arabic', 'Arial', 'DejaVu Sans']

            df = self.get_history_dataframe()
            if df.empty:
                self.stat_card_days.setText("📅 الأيام المسجلة: 0")
                self.stat_card_lessons.setText("📘 إجمالي الحصص: 0")
                self.stat_card_classes.setText("🏫 الأقسام المسجلة: 0")
                self.stats_table.setRowCount(0)
                return

            total_lessons = len(df)
            total_days = df['date'].nunique() if 'date' in df.columns else 0
            total_classes = df['classe'].nunique() if 'classe' in df.columns else 0

            # تحديث البطاقات الإحصائية
            self.stat_card_days.setText(f"📅 الأيام المسجلة: {total_days}")
            self.stat_card_lessons.setText(f"📘 إجمالي الحصص: {total_lessons}")
            self.stat_card_classes.setText(f"🏫 الأقسام المسجلة: {total_classes}")

            # استخدام Pandas لتجميع البيانات حسب المجال (majal)
            if 'majal' in df.columns:
                stats_df = df['majal'].value_counts().reset_index()
                stats_df.columns = ['majal', 'count']
                stats_df['percentage'] = (stats_df['count'] / total_lessons) * 100

                # تعبئة الجدول بالبيانات المجمعة
                self.stats_table.setRowCount(0)
                for _, row in stats_df.iterrows():
                    r = self.stats_table.rowCount()
                    self.stats_table.insertRow(r)
                    self.stats_table.setItem(r, 0, QTableWidgetItem(str(row['majal'])))
                    self.stats_table.setItem(r, 1, QTableWidgetItem(str(row['count'])))
                    self.stats_table.setItem(r, 2, QTableWidgetItem(f"{row['percentage']:.1f}%"))

                # رسم المخطط البياني العمودي (Vertical Bar Chart) بألوان جذابة متناسقة مع الـ Style
                if hasattr(self, 'ax') and hasattr(self, 'canvas'):
                    self.ax.clear()
                    
                    # لوحة ألوان عصرية ومتناسقة (تتطابق مع الثيمات الحديثة)
                    palette_colors = ['#3498db', '#2ecc71', '#e74c3c', '#f39c12', '#9b59b6', '#1abc9c', '#34495e']
                    colors = [palette_colors[i % len(palette_colors)] for i in range(len(stats_df))]
                    
                    bars = self.ax.bar(
                        stats_df['majal'].astype(str), 
                        stats_df['count'], 
                        color=colors, 
                        edgecolor='#2c3e50', 
                        linewidth=1.2,
                        width=0.55,
                        alpha=0.9
                    )
                    
                    # تخصيص عناوين المحاور والتصميم الجمالي للـ Graph
                    self.ax.set_title("توزيع الحصص حسب المجالات التعليمية", fontsize=13, fontweight='bold', pad=15, color='#2c3e50')
                    self.ax.set_xlabel("المجال التعليمي", fontsize=10, fontweight='bold', labelpad=10)
                    self.ax.set_ylabel("عدد الحصص", fontsize=10, fontweight='bold', labelpad=10)
                    
                    # تدوير أسماء المجالات قليلاً لتجنب التداخل وضمان الوضوح
                    plt.setp(self.ax.get_xticklabels(), rotation=20, ha='right', fontsize=9, fontweight='bold')
                    
                    self.ax.grid(axis='y', linestyle='--', alpha=0.5)
                    
                    # إظهار القيمة الرقمية فوق كل عمود
                    for bar in bars:
                        height = bar.get_height()
                        self.ax.text(
                            bar.get_x() + bar.get_width()/2., 
                            height + 0.2, 
                            f'{int(height)}', 
                            ha='center', 
                            va='bottom', 
                            fontsize=9, 
                            fontweight='bold', 
                            color='#2c3e50'
                        )

                    self.fig.tight_layout()
                    self.canvas.draw()
        except Exception as e:
            print(f"Error loading statistics: {e}")

    def apply_graph_style(self, fig, ax):
        """تطبيق تصميم واجهة التطبيق (Style.qss) على المخطط البياني"""
        # لون خلفية لوحة الرسم ليتطابق مع الخلفية العامة للنافذة
        fig.patch.set_facecolor('#ffffff')
        ax.set_facecolor('#f8f9fa')
        
        # إزالة الإطارات العلوية واليمنى لإعطاء مظهر عصري (Flat Design)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        # تنسيق إطارات المحاور السفلية واليسرى لتتطابق مع حدود الحقول والبطاقات
        ax.spines['left'].set_color('#ced4da')
        ax.spines['bottom'].set_color('#ced4da')
        ax.spines['left'].set_linewidth(1.0)
        ax.spines['bottom'].set_linewidth(1.0)
        
        # خطوط الشبكة الخلفية بلون هادئ وغير مزعج
        ax.grid(axis='y', linestyle='--', alpha=0.6, color='#e9ecef')
        ax.set_axisbelow(True)
        
        # تنسيق النصوص والأرقام على المحاور بلون متناسق مع النصوص العادية
        ax.tick_params(colors='#495057', labelsize=9, width=1)
        for label in ax.get_xticklabels() + ax.get_yticklabels():
            label.set_fontweight('bold')

    def toggle_enseig_info(self):
        row = self.db.school_info()
        current_values = list(row) if row else ["2026-2027", "", "", "", ""]
        fields = [
            ("السنة الدراسية", "text", "2026-2027"),
            ("المؤسسة", "text", ""),
            ("المعلم", "text", ""),
            ("المتفقد", "text", ""),
            ("الرتبة", "text", "")
        ]
        dlg = EntryDialog("بيانات المعلم والمؤسسة", fields, values=current_values, parent=self)
        if dlg.exec():
            values = dlg.values()
            if not values[0]:
                QMessageBox.warning(self, "تنبيه", "يرجى إدخال السنة الدراسية.")
                return
            self.db.update_school_info(values)
            for w, val in zip([self.year_edit, self.school_edit, self.teacher_edit, self.inspector_edit, self.grade_edit], values):
                w.setText(val or "")
            self.statusBar().showMessage("تم حفظ بيانات المؤسسة والمعلم بنجاح.", 3000)

    def make_table(self, headers):
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setMinimumHeight(120)
        return table

    def load_school_info(self):
        row = self.db.school_info()
        if row:
            for w, value in zip(
                [self.year_edit, self.school_edit, self.teacher_edit, self.inspector_edit, self.grade_edit], row
            ):
                w.setText(value or "")

    def save_school_info(self):
        values = [self.year_edit.text().strip(), self.school_edit.text().strip(),
                  self.teacher_edit.text().strip(), self.inspector_edit.text().strip(),
                  self.grade_edit.text().strip()]
        if not values[0]:
            QMessageBox.warning(self, "تنبيه", "يرجى إدخال السنة الدراسية.")
            return
        self.db.update_school_info(values)
        self.statusBar().showMessage("تم حفظ بيانات المؤسسة.", 3000)
        self.school_box.setVisible(False)

    def load_day(self, *_):
        qd = self.date_edit.date()
        day = qd.toString("yyyy-MM-dd")
        self.day_id = self.db.get_day_id(day)
        self.selected_lesson_id = None
        self.selected_activity_id = None

        if hasattr(self, 'custom_calendar'):
            self.custom_calendar.refresh_recorded_dates()
            self.custom_calendar.update()
        
        self.activity_table.setRowCount(0)
        self.detail_table.setRowCount(0)
        self.refresh_lessons()
        self.day_status.setText(f"التاريخ: {day} — عدد الحصص: {self.lesson_table.rowCount()}")

    def fill_table(self, table, rows):
        table.setRowCount(0)
        for row in rows:
            r = table.rowCount()
            table.insertRow(r)
            for col, value in enumerate(row):
                item = QTableWidgetItem("" if value is None else str(value))
                if col == 0:
                    item.setData(Qt.UserRole, value)
                table.setItem(r, col, item)
        table.resizeRowsToContents()

    def current_id(self, table):
        row = table.currentRow()
        if row < 0:
            return None
        item = table.item(row, 0)
        return int(item.text()) if item else None

    def refresh_lessons(self, select_id=None):
        rows = self.db.lessons(self.day_id)
        self.fill_table(self.lesson_table, rows)
        self.day_status.setText(f"التاريخ: {self.date_edit.date().toString('yyyy-MM-dd')} — عدد الحصص: {len(rows)}")
        
        if select_id:
            for r in range(self.lesson_table.rowCount()):
                if int(self.lesson_table.item(r, 0).text()) == select_id:
                    self.lesson_table.setCurrentCell(r, 0)
                    break
        elif self.lesson_table.rowCount() > 0:
            self.lesson_table.setCurrentCell(0, 0)

    def refresh_activities(self, select_id=None):
        if not self.selected_lesson_id:
            self.activity_table.setRowCount(0)
            return
        self.fill_table(self.activity_table, self.db.activities(self.selected_lesson_id))
        
        if select_id:
            for r in range(self.activity_table.rowCount()):
                if int(self.activity_table.item(r, 0).text()) == select_id:
                    self.activity_table.setCurrentCell(r, 0)
                    break
        elif self.activity_table.rowCount() > 0:
            self.activity_table.setCurrentCell(0, 0)

    def on_lesson_selected(self):
        self.selected_lesson_id = self.current_id(self.lesson_table)
        self.selected_activity_id = None
        self.detail_table.setRowCount(0)
        self.refresh_activities()

    def on_activity_selected(self):
        self.selected_activity_id = self.current_id(self.activity_table)
        self.refresh_details()

    def refresh_details(self, select_id=None):
        if not self.selected_activity_id:
            self.detail_table.setRowCount(0)
            return
        self.fill_table(self.detail_table, self.db.details(self.selected_activity_id))
        if select_id:
            for r in range(self.detail_table.rowCount()):
                if int(self.detail_table.item(r, 0).text()) == select_id:
                    self.detail_table.selectRow(r)
                    break

    def get_history_dataframe(self):
        try:
            con = self.db.connect()
            query = """
                SELECT h.classe, h.majal, h.heure, h.time, h.wehda_number, h.hessa_number, h.namat_taallom, d.date 
                FROM hessa h
                JOIN day_data d ON h.day_data_id = d.id
            """
            df = pd.read_sql(query, con=con)
            con.close()
            return df
        except Exception as e:
            print(f"History DF Error: {e}")
            return pd.DataFrame()

    def predict_lesson_with_pandas(self):
        try:
            df = self.get_history_dataframe()
            if df.empty:
                return None
            df['date'] = pd.to_datetime(df['date'])
            df['weekday_num'] = df['date'].dt.dayofweek
            target_num = self.date_edit.date().dayOfWeek() - 1
            df_filtered = df[df['weekday_num'] == target_num]
            if df_filtered.empty:
                return None
            existing_count = self.lesson_table.rowCount()
            if existing_count < len(df_filtered):
                common_classe = df_filtered['classe'].mode()[0] if not df_filtered['classe'].mode().empty else ""
                common_majal = df_filtered['majal'].mode()[0] if not df_filtered['majal'].mode().empty else ""
                common_heure = df_filtered['heure'].mode()[0] if not df_filtered['heure'].mode().empty else "08:00-09:00"
                common_time = df_filtered['time'].mode()[0] if not df_filtered['time'].mode().empty else "60 دقيقة"
                common_namat = df_filtered['namat_taallom'].mode()[0] if not df_filtered['namat_taallom'].mode().empty else "منهجي"
                return {
                    "classe": common_classe, "majal": common_majal,
                    "heure": common_heure, "time": common_time, "namat": common_namat
                }
        except Exception as e:
            print(f"Pandas Prediction Error: {e}")
        return None

    def add_lesson(self):
        df_history = self.get_history_dataframe()
        def_hessa_num = max(1, self.lesson_table.rowCount() + 1)
        default_vals = ["", "", "08:00-09:00", "60 دقيقة", 1, def_hessa_num, "منهجي"]
        predicted = self.predict_lesson_with_pandas()
        if predicted:
            default_vals[0] = predicted.get("classe", "")
            default_vals[1] = predicted.get("majal", "")
            default_vals[2] = predicted.get("heure", "08:00-09:00")
            default_vals[3] = predicted.get("time", "60 دقيقة")
            default_vals[4] = predicted.get("wehda", 1)
            default_vals[5] = def_hessa_num
            default_vals[6] = predicted.get("namat", "منهجي")

        dlg = LessonEntryDialog("إضافة حصة", df_history, default_values=default_vals, parent=self)
        if dlg.exec():
            v = dlg.values()
            if not v[0] or not v[1]:
                QMessageBox.warning(self, "بيانات ناقصة", "يرجى إدخال القسم والمجال / المادة.")
                return
            new_id = self.db.save_lesson(v, self.day_id)
            self.refresh_lessons(new_id)

    def edit_lesson(self):
        lid = self.current_id(self.lesson_table)
        if not lid:
            return self.warn_select("حصة")
        row = self.db.lesson(lid)
        current_values = [row[1], row[2], row[3], row[4], row[5], row[6], row[7]]
        df_history = self.get_history_dataframe()
        dlg = LessonEntryDialog("تعديل حصة", df_history, default_values=current_values, parent=self)
        if dlg.exec():
            v = dlg.values()
            if not v[0] or not v[1]:
                return QMessageBox.warning(self, "بيانات ناقصة", "القسم والمادة مطلوبان.")
            self.db.save_lesson(v, self.day_id, lid)
            self.refresh_lessons(lid)

    def delete_lesson(self):
        lid = self.current_id(self.lesson_table)
        if not lid:
            return self.warn_select("حصة")
        if self.confirm("حذف الحصة المحددة وكل أنشطتها وخصائصها؟"):
            self.db.delete_lesson(lid)
            self.selected_lesson_id = None
            self.refresh_lessons()
            self.activity_table.setRowCount(0); self.detail_table.setRowCount(0)

    def copy_selected_lessons(self):
        selected_rows = self.lesson_table.selectionModel().selectedRows()
        if not selected_rows:
            return self.warn_select("حصة واحدة على الأقل لنسخها")
        
        self.copied_lessons = []
        for index in selected_rows:
            row_idx = index.row()
            item = self.lesson_table.item(row_idx, 0)
            if not item:
                continue
            lesson_id = int(item.text())
            lesson_row = self.db.lesson(lesson_id)
            if not lesson_row:
                continue
            
            lesson_data = {
                "classe": lesson_row[1],
                "majal": lesson_row[2],
                "heure": lesson_row[3],
                "time": lesson_row[4],
                "wehda_number": lesson_row[5],
                "hessa_number": lesson_row[6],
                "namat_taallom": lesson_row[7],
                "activities": []
            }
            
            acts = self.db.activities(lesson_id)
            for act in acts:
                act_id, act_title, act_time = act[0], act[1], act[2]
                details = self.db.details(act_id)
                act_data = {
                    "title": act_title,
                    "time": act_time,
                    "details": [(d[1], d[2]) for d in details]
                }
                lesson_data["activities"].append(act_data)
                
            self.copied_lessons.append(lesson_data)
            
        self.statusBar().showMessage(f"تم نسخ {len(self.copied_lessons)} حصة بنجاح.", 3000)

    def paste_lessons(self):
        if not self.copied_lessons:
            QMessageBox.warning(self, "تنبيه", "لا توجد حصص منسوخة حالياً.")
            return
        if not self.day_id:
            QMessageBox.warning(self, "تنبيه", "يرجى تحديد اليوم المراد لصق الحصص فيه.")
            return
            
        try:
            with self.db.connect() as con:
                cursor = con.cursor()
                for les in self.copied_lessons:
                    cursor.execute("""
                        INSERT INTO hessa(classe, majal, heure, time, wehda_number, hessa_number, namat_taallom, day_data_id) 
                        VALUES(?,?,?,?,?,?,?,?)
                    """, (
                        les["classe"], les["majal"], les["heure"], les["time"],
                        les["wehda_number"], les["hessa_number"], les["namat_taallom"], self.day_id
                    ))
                    new_hessa_id = cursor.lastrowid
                    
                    for act in les["activities"]:
                        cursor.execute("""
                            INSERT INTO nachat(title, time, hessa_id) VALUES(?,?,?)
                        """, (act["title"], act["time"], new_hessa_id))
                        new_nachat_id = cursor.lastrowid
                        
                        for detail in act["details"]:
                            cursor.execute("""
                                INSERT INTO nachat_detail(key_name, value_text, nachat_id) VALUES(?,?,?)
                            """, (detail[0], detail[1], new_nachat_id))
                con.commit()
                
            self.refresh_lessons()
            self.statusBar().showMessage("تم لصق الحصص المنسوخة بنجاح.", 3000)
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"حدث خطأ أثناء لصق الحصص: {e}")

    def _current_lesson_context(self):
        if not self.selected_lesson_id:
            return "", "", None
        row = self.db.lesson(self.selected_lesson_id)
        if not row:
            return "", "", None
        return str(row[2] or ""), str(row[7] or ""), row[8]

    def add_activity(self):
        if not self.selected_lesson_id:
            return self.warn_select("حصة أولاً")
        majal, _namat, _day_data_id = self._current_lesson_context()
        weekday = self.date_edit.date().dayOfWeek() - 1
        dlg = ActivityEntryDialog("إضافة نشاط", majal, self.db, weekday, parent=self)
        if dlg.exec():
            title, duration = dlg.values()
            if not title:
                return QMessageBox.warning(self, "بيانات ناقصة", "عنوان النشاط مطلوب.")
            aid = self.db.save_activity(title, duration, self.selected_lesson_id)
            self.refresh_activities(aid)

    def edit_activity(self):
        aid = self.current_id(self.activity_table)
        if not aid:
            return self.warn_select("نشاط")
        majal, _namat, _day_data_id = self._current_lesson_context()
        row = next((x for x in self.db.activities(self.selected_lesson_id) if x[0] == aid), None)
        if not row:
            return
        weekday = self.date_edit.date().dayOfWeek() - 1
        dlg = ActivityEntryDialog("تعديل نشاط", majal, self.db, weekday,
                                  values=[row[1], row[2]], parent=self)
        if dlg.exec():
            title, duration = dlg.values()
            if not title:
                return QMessageBox.warning(self, "بيانات ناقصة", "عنوان النشاط مطلوب.")
            self.db.save_activity(title, duration, self.selected_lesson_id, aid)
            self.refresh_activities(aid)

    def delete_activity(self):
        aid = self.current_id(self.activity_table)
        if not aid:
            return self.warn_select("نشاط")
        if self.confirm("حذف النشاط المحدد وكل خصائصه؟"):
            self.db.delete_activity(aid)
            self.selected_activity_id = None
            self.refresh_activities()
            self.detail_table.setRowCount(0)

    def _detail_dialog_context(self):
        majal, namat, _day_data_id = self._current_lesson_context()
        activity_row = next((x for x in self.db.activities(self.selected_lesson_id or -1)
                             if x[0] == self.selected_activity_id), None)
        activity_title = activity_row[1] if activity_row else ""
        return namat, activity_title

    def add_detail(self):
        if not self.selected_activity_id:
            return self.warn_select("نشاط أولاً")
        namat, activity_title = self._detail_dialog_context()
        current_details = self.db.details(self.selected_activity_id)
        current_count = len(current_details)
        
        dlg = DetailEntryDialog("إضافة خاصية للنشاط", namat, activity_title,
                                self.db, current_count=current_count, parent=self)
        if dlg.exec():
            key, value = dlg.values()
            if not key:
                return QMessageBox.warning(self, "بيانات ناقصة", "يرجى اختيار اسم الخاصية.")
            if any(d[1] == key for d in current_details):
                reply = QMessageBox.question(
                    self,
                    "تنبيه: خاصية موجودة مسبقاً",
                    f"اسم الخاصية '{key}' موجود مسبقاً لهذا النشاط.\nهل تريد متابعة الإضافَة رغم ذلك؟",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply == QMessageBox.No:
                    return
            did = self.db.save_detail(key, value, self.selected_activity_id)
            self.refresh_details(did)

    def edit_detail(self):
        did = self.current_id(self.detail_table)
        if not did:
            return self.warn_select("خاصية")
        row = next((x for x in self.db.details(self.selected_activity_id) if x[0] == did), None)
        if not row:
            return
        namat, activity_title = self._detail_dialog_context()
        dlg = DetailEntryDialog("تعديل خاصية", namat, activity_title, self.db,
                                values=[row[1], row[2]], parent=self)
        if dlg.exec():
            key, value = dlg.values()
            if not key:
                return QMessageBox.warning(self, "بيانات ناقصة", "يرجى اختيار اسم الخاصية.")
            self.db.save_detail(key, value, self.selected_activity_id, did)
            self.refresh_details(did)

    def delete_detail(self):
        did = self.current_id(self.detail_table)
        if not did:
            return self.warn_select("خاصية")
        if self.confirm("هل تريد حذف الخاصية المحددة؟"):
            self.db.delete_detail(did)
            self.refresh_details()

    def warn_select(self, what):
        QMessageBox.information(self, "تحديد مطلوب", f"يرجى تحديد {what} من الجدول.")

    def confirm(self, message):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("تأكيد العملية")
        msg_box.setText(message)
        msg_box.setIcon(QMessageBox.Question)
        
        btn_yes = msg_box.addButton("نعم", QMessageBox.AcceptRole)
        btn_no = msg_box.addButton("إلغاء", QMessageBox.RejectRole)
        
        msg_box.exec()
        return msg_box.clickedButton() == btn_yes

    def export_odt_from_db_dialog(self):
        # 1. إظهار حوار اختيار اليوم مع التقويم المخصص
        dlg = DaySelectionDialog(self.db, parent=self)
        if not dlg.exec():
            return  # إذا ألغى المستخدم العملية
        
        selected_date_text = dlg.get_selected_date_str()
        
        # 2. تنفيذ عملية التصدير بنفس منطقك السابق ولكن باستخدام التاريخ المختار
        formatter = SchoolDataFormatter(str(DB_PATH))
        formatted_db_date = formatter.normalize_date(selected_date_text)
        
        with formatter.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, date FROM day_data WHERE date = ?", (formatted_db_date,))
            day_row = cursor.fetchone()
            if not day_row:
                QMessageBox.information(self, "تنبيه", f"لا توجد بيانات مسجلة للتاريخ: {selected_date_text}")
                return False
            cursor.execute("SELECT id, classe, majal, heure, time, wehda_number, hessa_number, namat_taallom FROM hessa WHERE day_data_id = ? ORDER BY id ASC", (day_row["id"],))
            hessa_rows = cursor.fetchall()
            lessons_data = []
            for h in hessa_rows:
                cursor.execute("SELECT id, title, time FROM nachat WHERE hessa_id = ? ORDER BY id ASC", (h["id"],))
                nachat_rows = cursor.fetchall()
                activities = []
                for n in nachat_rows:
                    cursor.execute("SELECT key_name, value_text FROM nachat_detail WHERE nachat_id = ? ORDER BY id ASC", (n["id"],))
                    details = cursor.fetchall()
                    activities.append({"title": n["title"], "time": n["time"] if n["time"] else "", "details": details})
                lessons_data.append({"majal": h["majal"] if h["majal"] else "", "classe": h["classe"] if h["classe"] else "", "heure": h["heure"] if h["heure"] else "", "time": h["time"] if h["time"] else "", "wehda": h["wehda_number"], "hessa": h["hessa_number"], "namat": h["namat_taallom"] if h["namat_taallom"] else "", "activities": activities})
        
        date_obj = datetime.strptime(day_row["date"], "%Y-%m-%d")
        days_ar = ["الإثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]
        months_ar = ["جانفي", "فيفري", "مارس", "أفريل", "ماي", "جوان", "جويلية", "أوت", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]
        day_name = days_ar[date_obj.weekday()]
        day_num = f"{date_obj.day:02d}"
        month_name = months_ar[date_obj.month - 1]
        year_num = date_obj.year

        report_content = f"يوم{' '*20}{day_name}{' '*20}{day_num}{' '*20}{month_name}{' '*20}{year_num}\n" + "ـ." * 30 + "\n"
        if not lessons_data:
            report_content += "لا توجد حصص مسجلة لهذا اليوم.\n"
        else:
            for les in lessons_data:
                time_value = str(les["time"])
                time_str = time_value if "دق" in time_value else f"{time_value} دق"
                report_content += f"■ القسم: {les['classe']}  | المجال: {les['majal']}  | {les['heure']}  | {time_str}  | الوحدة: {les['wehda']}  | الحصة: {les['hessa']}  | {les['namat']}\n"
                for act in les["activities"]:
                    act_time_value = str(act["time"])
                    act_time = act_time_value if "دق" in act_time_value else f"{act_time_value} دق"
                    report_content += f"    ◄ {act['title']}: {act_time}\n"
                    for dt in act["details"]:
                        report_content += f"        ├─ {dt['key_name']}: {dt['value_text']}\n"
                report_content += "ـ." * 30 + "\n"

        docs_dir = Path.home() / "Documents"
        docs_dir.mkdir(parents=True, exist_ok=True)
        output_pdf_p = docs_dir / f"school_report_{selected_date_text}.pdf"

        try:
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(str(output_pdf_p))
            page_layout = QPageLayout(QPageSize(QPageSize.PageSizeId.A4), QPageLayout.Orientation.Portrait, QMarginsF(1, 1, 1, 1), QPageLayout.Unit.Millimeter)
            printer.setPageLayout(page_layout)
            doc = QTextDocument()
            doc.setDefaultFont(QFont("Noto Naskh Arabic", 8))
            doc.setPlainText(report_content)
            printable_rect = printer.pageLayout().paintRect(QPageLayout.Unit.Point)
            doc.setPageSize(printable_rect.size())
            cursor = QTextCursor(doc)
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
            block_format = QTextBlockFormat()
            block_format.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cursor.setBlockFormat(block_format)
            char_format = QTextCharFormat()
            char_format.setFontWeight(QFont.Weight.Bold)
            cursor.mergeCharFormat(char_format)
            doc.print_(printer)

            system_platform = platform.system()
            if system_platform == "Windows":
                os.startfile(str(output_pdf_p))
            elif system_platform == "Darwin":
                subprocess.run(["open", str(output_pdf_p)])
            else:
                subprocess.Popen(["xdg-open", str(output_pdf_p)])
            self.statusBar().showMessage(f"تم تصدير وفتح التقرير في المستندات بنجاح.", 3000)
            return True
        except Exception as e:
            QMessageBox.critical(self, "خطأ في التصدير", f"حدث خطأ أثناء إنشاء الملف: {e}")
            return False

    def export_day_to_json(self):
        import json
        
        # 1. إظهار حوار اختيار اليوم باستخدام التقويم المخصص
        dlg = DaySelectionDialog(self.db, parent=self)
        if not dlg.exec():
            return  # إذا ألغى المستخدم العملية
        
        selected_date_text = dlg.get_selected_date_str()
        
        # 2. جلب وتصدير بيانات اليوم المحدد
        formatter = SchoolDataFormatter(str(DB_PATH))
        formatted_db_date = formatter.normalize_date(selected_date_text)
        
        with formatter.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT d.id AS day_id, d.date, a.nom_annee, a.nom_ecole, a.nom_enseignant, a.nom_inspecteur, a.grade FROM day_data d JOIN ann_scolaire a ON d.ann_scolaire_id = a.id WHERE d.date = ?", (formatted_db_date,))
            day_row = cursor.fetchone()
            if not day_row:
                QMessageBox.information(self, "تنبيه", f"لا توجد بيانات مسجلة للتاريخ: {selected_date_text}")
                return False
                
            day_data = {
                "date": day_row["date"],
                "school_info": {
                    "nom_annee": day_row["nom_annee"], 
                    "nom_ecole": day_row["nom_ecole"], 
                    "nom_enseignant": day_row["nom_enseignant"], 
                    "nom_inspecteur": day_row["nom_inspecteur"], 
                    "grade": day_row["grade"]
                },
                "lessons": []
            }
            
            cursor.execute("SELECT id, classe, majal, heure, time, wehda_number, hessa_number, namat_taallom FROM hessa WHERE day_data_id = ? ORDER BY id ASC", (day_row["day_id"],))
            hessa_rows = cursor.fetchall()
            
            for h in hessa_rows:
                lesson_dict = {
                    "id": h["id"], "classe": h["classe"], "majal": h["majal"], 
                    "heure": h["heure"], "time": h["time"], "wehda_number": h["wehda_number"], 
                    "hessa_number": h["hessa_number"], "namat_taallom": h["namat_taallom"], "activities": []
                }
                
                cursor.execute("SELECT id, title, time FROM nachat WHERE hessa_id = ? ORDER BY id ASC", (h["id"],))
                nachat_rows = cursor.fetchall()
                
                for n in nachat_rows:
                    activity_dict = {"id": n["id"], "title": n["title"], "time": n["time"], "details": []}
                    cursor.execute("SELECT key_name, value_text FROM nachat_detail WHERE nachat_id = ? ORDER BY id ASC", (n["id"],))
                    detail_rows = cursor.fetchall()
                    
                    for d in detail_rows:
                        activity_dict["details"].append({"key_name": d["key_name"], "value_text": d["value_text"]})
                        
                    lesson_dict["activities"].append(activity_dict)
                    
                day_data["lessons"].append(lesson_dict)
            
            docs_dir = Path.home() / "Documents"
            docs_dir.mkdir(parents=True, exist_ok=True)
            filename = docs_dir / f"school_day_{day_row['date']}.json"
            
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(day_data, f, ensure_ascii=False, indent=4)
                
            QMessageBox.information(self, "نجاح التصدير", f"تم تصدير بيانات يوم {day_row['date']} بنجاح إلى مجلد المستندات:\n{filename}")
            return True

    
    def import_day_from_json(self):
        import json
        from PySide6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(self, "اختيار ملف JSON للاستيراد", str(APP_DIR), "JSON Files (*.json);;All Files (*)")
        if not file_path:
            return
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                day_data = json.load(f)
            target_date = day_data.get("date")
            if not target_date:
                QMessageBox.warning(self, "خطأ في الملف", "ملف JSON لا يحتوي على حقل التاريخ (date).")
                return
            with self.db.connect() as con:
                cursor = con.cursor()
                cursor.execute("SELECT id FROM day_data WHERE date = ? AND ann_scolaire_id = ?", (target_date, self.db.year_id))
                existing_day = cursor.fetchone()
                if existing_day:
                    old_day_id = existing_day[0]
                    cursor.execute("DELETE FROM day_data WHERE id = ?", (old_day_id,))
                cursor.execute("INSERT INTO day_data (date, ann_scolaire_id) VALUES (?, ?)", (target_date, self.db.year_id))
                new_day_id = cursor.lastrowid
                for lesson in day_data.get("lessons", []):
                    cursor.execute("INSERT INTO hessa (classe, majal, heure, time, wehda_number, hessa_number, namat_taallom, day_data_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (lesson.get("classe", ""), lesson.get("majal", ""), lesson.get("heure", ""), lesson.get("time", ""), lesson.get("wehda_number", 1), lesson.get("hessa_number", 1), lesson.get("namat_taallom", ""), new_day_id))
                    new_hessa_id = cursor.lastrowid
                    for activity in lesson.get("activities", []):
                        cursor.execute("INSERT INTO nachat (title, time, hessa_id) VALUES (?, ?, ?)", (activity.get("title", ""), activity.get("time", ""), new_hessa_id))
                        new_nachat_id = cursor.lastrowid
                        for detail in activity.get("details", []):
                            cursor.execute("INSERT INTO nachat_detail (key_name, value_text, nachat_id) VALUES (?, ?, ?)", (detail.get("key_name", ""), detail.get("value_text", ""), new_nachat_id))
                con.commit()
            qd = QDate.fromString(target_date, "yyyy-MM-dd")
            if qd.isValid():
                self.date_edit.setDate(qd)
            self.load_day()
            QMessageBox.information(self, "نجاح الاستيراد", f"تم استيراد بيانات يوم {target_date} بنجاح وتسجيلها في التطبيق.")
        except Exception as e:
            QMessageBox.critical(self, "خطأ في الاستيراد", f"حدث خطأ أثناء قراءة أو استيراد ملف JSON:\n{e}")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if len(urls) == 1 and urls[0].toLocalFile().endswith('.json'):
                event.acceptProposedAction()
                return
        event.ignore()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            if file_path:
                self.process_json_import(file_path)

    def import_all_years_from_json(self):
        from PySide6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(self, "اختيار ملف JSON السنوي للاستيراد", str(Path.home() / "Documents"), "JSON Files (*.json);;All Files (*)")
        if not file_path:
            return
        self.process_json_import(file_path)

    def process_json_import(self, file_path):
        import json
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            if "days" in data:
                school_info = data.get("school_info", {})
                default_year_name = school_info.get("nom_annee", "2026-2027")
                
                dlg = YearImportDialog(self.db, default_year_name=default_year_name, parent=self)
                if not dlg.exec():
                    return
                target_year_name = dlg.get_selected_year_name()
                if not target_year_name:
                    QMessageBox.warning(self, "تنبيه", "اسم السنة الدراسية مطلوب.")
                    return

                with self.db.connect() as con:
                    cursor = con.cursor()
                    cursor.execute("SELECT id FROM ann_scolaire WHERE nom_annee = ?", (target_year_name,))
                    row = cursor.fetchone()
                    if row:
                        target_year_id = row[0]
                        cursor.execute("""
                            UPDATE ann_scolaire 
                            SET nom_ecole = ?, nom_enseignant = ?, nom_inspecteur = ?, grade = ? 
                            WHERE id = ?
                        """, (
                            school_info.get("nom_ecole", ""),
                            school_info.get("nom_enseignant", ""),
                            school_info.get("nom_inspecteur", ""),
                            school_info.get("grade", ""),
                            target_year_id
                        ))
                    else:
                        cursor.execute("""
                            INSERT INTO ann_scolaire (nom_annee, nom_ecole, nom_enseignant, nom_inspecteur, grade) 
                            VALUES (?, ?, ?, ?, ?)
                        """, (
                            target_year_name,
                            school_info.get("nom_ecole", ""),
                            school_info.get("nom_enseignant", ""),
                            school_info.get("nom_inspecteur", ""),
                            school_info.get("grade", "")
                        ))
                        target_year_id = cursor.lastrowid

                    imported_days_count = 0
                    for day_item in data.get("days", []):
                        target_date = day_item.get("date")
                        if not target_date:
                            continue
                        
                        cursor.execute("SELECT id FROM day_data WHERE date = ? AND ann_scolaire_id = ?", (target_date, target_year_id))
                        existing_day = cursor.fetchone()
                        if existing_day:
                            cursor.execute("DELETE FROM day_data WHERE id = ?", (existing_day[0],))
                        
                        cursor.execute("INSERT INTO day_data (date, ann_scolaire_id) VALUES (?, ?)", (target_date, target_year_id))
                        new_day_id = cursor.lastrowid
                        
                        for lesson in day_item.get("lessons", []):
                            cursor.execute("""
                                INSERT INTO hessa (classe, majal, heure, time, wehda_number, hessa_number, namat_taallom, day_data_id) 
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                lesson.get("classe", ""), lesson.get("majal", ""), lesson.get("heure", ""), 
                                lesson.get("time", ""), lesson.get("wehda_number", 1), lesson.get("hessa_number", 1), 
                                lesson.get("namat_taallom", ""), new_day_id
                            ))
                            new_hessa_id = cursor.lastrowid
                            
                            for activity in lesson.get("activities", []):
                                cursor.execute("INSERT INTO nachat (title, time, hessa_id) VALUES (?, ?, ?)", (activity.get("title", ""), activity.get("time", ""), new_hessa_id))
                                new_nachat_id = cursor.lastrowid
                                
                                for detail in activity.get("details", []):
                                    cursor.execute("INSERT INTO nachat_detail (key_name, value_text, nachat_id) VALUES (?, ?, ?)", (detail.get("key_name", ""), detail.get("value_text", ""), new_nachat_id))
                        
                        imported_days_count += 1
                    con.commit()

                self.load_school_info()
                self.load_day()
                QMessageBox.information(self, "نجاح الاستيراد الشامل", f"تم استيراد السنة الدراسية بكافة أيامها ({imported_days_count} يوم) بنجاح!")

            else:
                target_date = data.get("date")
                if not target_date:
                    QMessageBox.warning(self, "خطأ في الملف", "ملف JSON لا يحتوي على حقل التاريخ (date) أو بيانات صحيحة.")
                    return
                with self.db.connect() as con:
                    cursor = con.cursor()
                    cursor.execute("SELECT id FROM day_data WHERE date = ? AND ann_scolaire_id = ?", (target_date, self.db.year_id))
                    existing_day = cursor.fetchone()
                    if existing_day:
                        cursor.execute("DELETE FROM day_data WHERE id = ?", (existing_day[0],))
                    cursor.execute("INSERT INTO day_data (date, ann_scolaire_id) VALUES (?, ?)", (target_date, self.db.year_id))
                    new_day_id = cursor.lastrowid
                    for lesson in data.get("lessons", []):
                        cursor.execute("INSERT INTO hessa (classe, majal, heure, time, wehda_number, hessa_number, namat_taallom, day_data_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (lesson.get("classe", ""), lesson.get("majal", ""), lesson.get("heure", ""), lesson.get("time", ""), lesson.get("wehda_number", 1), lesson.get("hessa_number", 1), lesson.get("namat_taallom", ""), new_day_id))
                        new_hessa_id = cursor.lastrowid
                        for activity in lesson.get("activities", []):
                            cursor.execute("INSERT INTO nachat (title, time, hessa_id) VALUES (?, ?, ?)", (activity.get("title", ""), activity.get("time", ""), new_hessa_id))
                            new_nachat_id = cursor.lastrowid
                            for detail in activity.get("details", []):
                                cursor.execute("INSERT INTO nachat_detail (key_name, value_text, nachat_id) VALUES (?, ?, ?)", (detail.get("key_name", ""), detail.get("value_text", ""), new_nachat_id))
                    con.commit()
                qd = QDate.fromString(target_date, "yyyy-MM-dd")
                if qd.isValid():
                    self.date_edit.setDate(qd)
                self.load_day()
                QMessageBox.information(self, "نجاح الاستيراد", f"تم استيراد بيانات يوم {target_date} بنجاح وتسجيلها في التطبيق.")

        except Exception as e:
            QMessageBox.critical(self, "خطأ في الاستيراد", f"حدث خطأ أثناء قراءة أو استيراد ملف JSON:\n{e}")

    def clear_current_day_lessons(self):
        if not self.day_id:
            return
        if self.confirm("هل أنت متأكد من مسح جميع حصص اليوم الحالي مع أنشطتها وخصائصها؟"):
            try:
                with self.db.connect() as con:
                    cursor = con.cursor()
                    cursor.execute("DELETE FROM hessa WHERE day_data_id = ?", (self.day_id,))
                    con.commit()
                self.selected_lesson_id = None
                self.selected_activity_id = None
                self.load_day()
                self.statusBar().showMessage("تم مسح جميع حصص اليوم بنجاح.", 3000)
            except Exception as e:
                QMessageBox.critical(self, "خطأ", f"حدث خطأ أثناء مسح حصص اليوم: {e}")

    def clear_all_lessons_in_db(self):
        if self.confirm("تحذير خطير: هل أنت متأكد من مسح جميع الحصص والأنشطة والخصائص في قاعدة البيانات بالكامل؟"):
            try:
                with self.db.connect() as con:
                    cursor = con.cursor()
                    cursor.execute("DELETE FROM nachat_detail")
                    cursor.execute("DELETE FROM nachat")
                    cursor.execute("DELETE FROM hessa")
                    con.commit()
                self.selected_lesson_id = None
                self.selected_activity_id = None
                self.load_day()
                self.statusBar().showMessage("تم مسح جميع الحصص في قاعدة البيانات بالكامل.", 3000)
            except Exception as e:
                QMessageBox.critical(self, "خطأ", f"حدث خطأ أثناء مسح جميع الحصص: {e}")

    def clear_all_activities_for_lesson(self):
        if not self.selected_lesson_id:
            return self.warn_select("حصة أولاً")
        if self.confirm("هل أنت متأكد من مسح جميع أنشطة هذه الحصة وخصائصها؟"):
            try:
                with self.db.connect() as con:
                    cursor = con.cursor()
                    cursor.execute("DELETE FROM nachat WHERE hessa_id = ?", (self.selected_lesson_id,))
                    con.commit()
                self.selected_activity_id = None
                self.refresh_activities()
                self.detail_table.setRowCount(0)
                self.statusBar().showMessage("تم مسح جميع أنشطة الحصة بنجاح.", 3000)
            except Exception as e:
                QMessageBox.critical(self, "خطأ", f"حدث خطأ أثناء مسح أنشطة الحصة: {e}")

    def clear_all_details_for_activity(self):
        if not self.selected_activity_id:
            return self.warn_select("نشاط أولاً")
        if self.confirm("هل أنت متأكد من مسح جميع خصائص هذا النشاط؟"):
            try:
                with self.db.connect() as con:
                    cursor = con.cursor()
                    cursor.execute("DELETE FROM nachat_detail WHERE nachat_id = ?", (self.selected_activity_id,))
                    con.commit()
                self.refresh_details()
                self.statusBar().showMessage("تم مسح جميع خصائص النشاط بنجاح.", 3000)
            except Exception as e:
                QMessageBox.critical(self, "خطأ", f"حدث خطأ أثناء مسح خصائص النشاط: {e}")

    def copy_activity_details(self):
        if not self.selected_activity_id:
            return self.warn_select("نشاط أولاً لنسخ خصائصه")
        details = self.db.details(self.selected_activity_id)
        if not details:
            QMessageBox.information(self, "تنبيه", "النشاط المحدد لا يحتوي على خصائص لنسخها.")
            return
        self.copied_details = [(d[1], d[2]) for d in details]
        self.statusBar().showMessage(f"تم نسخ {len(self.copied_details)} خاصية بنجاح.", 3000)

    def paste_activity_details(self):
        if not self.selected_activity_id:
            return self.warn_select("نشاط أولاً لصق الخصائص فيه")
        if not self.copied_details:
            QMessageBox.warning(self, "تنبيه", "لا توجد خصائص منسوخة حالياً.")
            return
        try:
            with self.db.connect() as con:
                cursor = con.cursor()
                for key_name, value_text in self.copied_details:
                    cursor.execute("INSERT INTO nachat_detail (key_name, value_text, nachat_id) VALUES (?, ?, ?)", (key_name, value_text, self.selected_activity_id))
                con.commit()
            self.refresh_details()
            self.statusBar().showMessage("تم لصق الخصائص بنجاح.", 3000)
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"حدث خطأ أثناء لصق الخصائص: {e}")

    def export_all_days_for_year(self):
        import json
        dlg = SchoolYearSelectionDialog(self.db, parent=self)
        if not dlg.exec():
            return
        
        year_id, year_name = dlg.get_selected_year_info()
        if not year_id:
            QMessageBox.warning(self, "تنبيه", "لم يتم تحديد سنة دراسية.")
            return

        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT nom_annee, nom_ecole, nom_enseignant, nom_inspecteur, grade FROM ann_scolaire WHERE id = ?", (year_id,))
                school_info_row = cursor.fetchone()
                school_info = {
                    "nom_annee": school_info_row[0] if school_info_row else "",
                    "nom_ecole": school_info_row[1] if school_info_row else "",
                    "nom_enseignant": school_info_row[2] if school_info_row else "",
                    "nom_inspecteur": school_info_row[3] if school_info_row else "",
                    "grade": school_info_row[4] if school_info_row else ""
                }

                cursor.execute("SELECT id, date FROM day_data WHERE ann_scolaire_id = ? ORDER BY date ASC", (year_id,))
                days = cursor.fetchall()
                
                if not days:
                    QMessageBox.information(self, "تنبيه", f"لا توجد أيام مسجلة للسنة الدراسية: {year_name}")
                    return

                all_days_data = {
                    "school_info": school_info,
                    "days": []
                }

                for day in days:
                    day_id = day[0]
                    day_date = day[1]
                    
                    day_entry = {
                        "date": day_date,
                        "lessons": []
                    }

                    cursor.execute("SELECT id, classe, majal, heure, time, wehda_number, hessa_number, namat_taallom FROM hessa WHERE day_data_id = ? ORDER BY id ASC", (day_id,))
                    hessa_rows = cursor.fetchall()
                    
                    for h in hessa_rows:
                        lesson_dict = {
                            "id": h[0], "classe": h[1], "majal": h[2], "heure": h[3],
                            "time": h[4], "wehda_number": h[5], "hessa_number": h[6],
                            "namat_taallom": h[7], "activities": []
                        }
                        
                        cursor.execute("SELECT id, title, time FROM nachat WHERE hessa_id = ? ORDER BY id ASC", (h[0],))
                        nachat_rows = cursor.fetchall()
                        
                        for n in nachat_rows:
                            activity_dict = {"id": n[0], "title": n[1], "time": n[2], "details": []}
                            cursor.execute("SELECT key_name, value_text FROM nachat_detail WHERE nachat_id = ? ORDER BY id ASC", (n[0],))
                            detail_rows = cursor.fetchall()
                            for d in detail_rows:
                                activity_dict["details"].append({"key_name": d[0], "value_text": d[1]})
                            lesson_dict["activities"].append(activity_dict)
                        day_entry["lessons"].append(lesson_dict)
                        
                    all_days_data["days"].append(day_entry)

                docs_dir = Path.home() / "Documents"
                docs_dir.mkdir(parents=True, exist_ok=True)
                safe_year_name = year_name.replace("/", "-")
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = docs_dir / f"school_year_{safe_year_name}_export_{timestamp}.json"

                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(all_days_data, f, ensure_ascii=False, indent=4)

                QMessageBox.information(
                    self, 
                    "نجاح التصدير الشامل", 
                    f"تم تصدير جميع أيام السنة الدراسية ({year_name}) بنجاح إلى مجلد المستندات:\n{filename}"
                )
                return True

        except Exception as e:
            QMessageBox.critical(self, "خطأ في التصدير", f"حدث خطأ أثناء تصدير بيانات السنة الدراسية:\n{e}")
            return False


def load_custom_font():
    if FONTS_DIR.exists() and FONTS_DIR.is_dir():
        font_files = list(FONTS_DIR.glob("*.ttf")) + list(FONTS_DIR.glob("*.otf"))
        if font_files:
            font_path = str(font_files[0])
            font_id = QFontDatabase.addApplicationFont(font_path)
            if font_id != -1:
                font_families = QFontDatabase.applicationFontFamilies(font_id)
                if font_families:
                    return font_families[0]
    return "Noto Naskh Arabic"


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setLayoutDirection(Qt.RightToLeft)

    custom_font_family = load_custom_font()
    app.setFont(QFont(custom_font_family, 10))

    style_file = APP_DIR / "style_1.qss"
    if style_file.exists():
        with open(style_file, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())

    window = SchoolPlanner()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
