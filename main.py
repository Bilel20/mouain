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
from datetime import datetime
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
    QMessageBox, QDialog, QDialogButtonBox, QTextEdit, QHeaderView, QAbstractItemView, QCompleter
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
ICON_PATH = BASE_DIR / "icons" / "icon.jpeg"
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
            lines.append(f"{" " * 30}📌 {formatted_date_header}")
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
            match = self.find_match(current_text)
            if match and match.startswith(current_text) and match != current_text:
                self.is_completing = True
                remainder = match[len(current_text):]
                pos = cursor.position()
                self.insertPlainText(remainder)
                cursor.setPosition(pos)
                cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
                self.setTextCursor(cursor)
                self.is_completing = False

    def find_match(self, prefix):
        if not prefix.strip():
            return ""
        key_name = self.key_combo.currentText()
        try:
            with self.db.connect() as con:
                cursor = con.cursor()
                cursor.execute("""
                    SELECT DISTINCT d.value_text 
                    FROM nachat_detail d
                    JOIN nachat n ON d.nachat_id = n.id
                    WHERE d.key_name = ? AND n.title = ? AND d.value_text LIKE ?
                """, (key_name, self.activity_title, f"{prefix}%"))
                row = cursor.fetchone()
                if row and row[0]:
                    return row[0]
        except Exception as e:
            print(f"Completion error: {e}")
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


class LessonEntryDialog(QDialog):
    def __init__(self, title, df_history, default_values=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(480)
        self.df_history = df_history
        
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
        
        self.combo_time = QComboBox()
        self.combo_time.setEditable(True)
        self.combo_time.addItems(["60 دقيقة", "45 دقيقة", "90 دقيقة", "120 دقيقة"])
        
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
        form.addRow("التوقيت", self.combo_heure)
        form.addRow("مدة الحصة", self.combo_time)
        form.addRow("الوحدة", self.spin_wehda)
        form.addRow("الحصة", self.spin_hessa)
        form.addRow("نمط التعلم", self.combo_namat)
        
        layout.addLayout(form)
        
        buttons = QDialogButtonBox()
        buttons.addButton("حفظ", QDialogButtonBox.AcceptRole)
        buttons.addButton("إلغاء", QDialogButtonBox.RejectRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.combo_classe.currentTextChanged.connect(self.on_classe_changed)
        
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

    def on_classe_changed(self, classe_text):
        if self.df_history is None or self.df_history.empty:
            return
        df_sub = self.df_history[self.df_history['classe'] == classe_text]
        if df_sub.empty:
            return
        majals = sorted(df_sub['majal'].dropna().unique().tolist())
        self.combo_majal.clear()
        self.combo_majal.addItems(majals)
        heures = sorted(df_sub['heure'].dropna().unique().tolist())
        self.combo_heure.clear()
        self.combo_heure.addItems(heures)
        times = sorted(df_sub['time'].dropna().unique().tolist())
        if times:
            self.combo_time.clear()
            self.combo_time.addItems(times)

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
        self.setStyleSheet("QLineEdit { qproperty-alignment: AlignCenter; }")
        self.showMaximized()
        self.setAcceptDrops(True)

    def build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

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
        root.addWidget(self.school_box)
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
        root.addWidget(agenda)

        splitter = QSplitter(Qt.Vertical)
        root.addWidget(splitter, 1)

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

        footer = QHBoxLayout()
        self.export_hint = QLabel("تُحفظ التغييرات مباشرة في قاعدة بيانات SQLite.")
        footer.addWidget(self.export_hint, 1)

        self.statusBar().showMessage(f"قاعدة البيانات: {DB_PATH}")
        toolbar = self.addToolBar("ملف")
        toggle_action = QAction("بيانات المعلم", self)
        toggle_action.triggered.connect(self.toggle_enseig_info)
        
        export_odt_action = QAction("تصدير إلى ملف pdf", self)
        export_odt_action.triggered.connect(lambda: self.export_odt_from_db(
            db_path=DB_PATH, 
            date_text=self.date_edit.date().toString("yyyy-MM-dd"),
            template_path=TEMPLATE_PATH,
            output_odt=APP_DIR / "output.odt",
            output_pdf=APP_DIR / "output.pdf"
        ))
        
        export_json_action = QAction("تصدير يوم", self)
        export_json_action.triggered.connect(self.export_day_to_json)
        import_json_action = QAction("استيراد يوم", self)
        import_json_action.triggered.connect(self.import_day_from_json)
        export_year_action = QAction("تصدير سنة دراسية كاملة (JSON)", self)
        export_year_action.triggered.connect(self.export_all_days_for_year)
        import_year_action = QAction("استيراد سنة دراسية كاملة (JSON)", self)
        import_year_action.triggered.connect(self.import_all_years_from_json)
        
        toolbar.addAction(toggle_action)
        toolbar.addAction(export_odt_action)
        toolbar.addAction(export_json_action)
        toolbar.addAction(import_json_action)
        toolbar.addAction(export_year_action)
        toolbar.addAction(import_year_action)

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

    def export_odt_from_db(self, db_path=DB_PATH, date_text=None, template_path=TEMPLATE_PATH, output_odt=None, output_pdf=None):
        if not isinstance(date_text, str):
            date_text = datetime.now().strftime("%Y-%m-%d")
        
        current_date_str = self.date_edit.date().toString("yyyy-MM-dd")
        formatter = SchoolDataFormatter(str(db_path))
        formatted_db_date = formatter.normalize_date(date_text)
        
        with formatter.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, date FROM day_data WHERE date = ?", (formatted_db_date,))
            day_row = cursor.fetchone()
            if not day_row:
                QMessageBox.information(self, "تنبيه", f"لا توجد بيانات مسجلة للتاريخ: {date_text}")
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
        output_pdf_p = docs_dir / f"school_report_{current_date_str}.pdf"

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
        date_text = self.date_edit.date().toString("yyyy-MM-dd")
        formatter = SchoolDataFormatter(str(DB_PATH))
        formatted_db_date = formatter.normalize_date(date_text)
        with formatter.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT d.id AS day_id, d.date, a.nom_annee, a.nom_ecole, a.nom_enseignant, a.nom_inspecteur, a.grade FROM day_data d JOIN ann_scolaire a ON d.ann_scolaire_id = a.id WHERE d.date = ?", (formatted_db_date,))
            day_row = cursor.fetchone()
            if not day_row:
                QMessageBox.information(self, "تنبيه", f"لا توجد بيانات مسجلة للتاريخ: {date_text}")
                return False
            day_data = {
                "date": day_row["date"],
                "school_info": {"nom_annee": day_row["nom_annee"], "nom_ecole": day_row["nom_ecole"], "nom_enseignant": day_row["nom_enseignant"], "nom_inspecteur": day_row["nom_inspecteur"], "grade": day_row["grade"]},
                "lessons": []
            }
            cursor.execute("SELECT id, classe, majal, heure, time, wehda_number, hessa_number, namat_taallom FROM hessa WHERE day_data_id = ? ORDER BY id ASC", (day_row["day_id"],))
            hessa_rows = cursor.fetchall()
            for h in hessa_rows:
                lesson_dict = {"id": h["id"], "classe": h["classe"], "majal": h["majal"], "heure": h["heure"], "time": h["time"], "wehda_number": h["wehda_number"], "hessa_number": h["hessa_number"], "namat_taallom": h["namat_taallom"], "activities": []}
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