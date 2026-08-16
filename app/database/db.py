import os
import sqlite3
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_path=None):
        if db_path is None:
            # Place database in the 'data' directory in the workspace
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            data_dir = os.path.join(base_dir, "data")
            os.makedirs(data_dir, exist_ok=True)
            db_path = os.path.join(data_dir, "focusbuddy.db")
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            # Goals & Events Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS goals_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    date TEXT NOT NULL,
                    time TEXT,
                    priority TEXT,
                    description TEXT,
                    preparation_topics TEXT,
                    target TEXT,
                    status TEXT DEFAULT 'Pending'
                )
            """)

            # Tasks Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    duration_minutes INTEGER DEFAULT 25,
                    priority TEXT DEFAULT 'Medium',
                    status TEXT DEFAULT 'Pending',
                    completed_at TEXT,
                    difficulty TEXT DEFAULT 'Medium',
                    category TEXT
                )
            """)

            # Focus Sessions Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS focus_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER,
                    duration_minutes INTEGER NOT NULL,
                    completed_minutes INTEGER DEFAULT 0,
                    type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    state TEXT NOT NULL,
                    FOREIGN KEY (task_id) REFERENCES tasks(id)
                )
            """)

            # Distraction Logs Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS distraction_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    window_title TEXT NOT NULL,
                    app_name TEXT,
                    timestamp TEXT NOT NULL,
                    session_id INTEGER,
                    FOREIGN KEY (session_id) REFERENCES focus_sessions(id)
                )
            """)

            # Daily Schedule Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schedule_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_name TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    duration_minutes INTEGER NOT NULL,
                    priority TEXT NOT NULL,
                    status TEXT DEFAULT 'Pending',
                    date TEXT NOT NULL
                )
            """)

            # Settings Key-Value Store
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            
            conn.commit()
        finally:
            conn.close()

    # --- SETTINGS UTILS ---
    def get_setting(self, key, default=None):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row[0] if row else default
        finally:
            conn.close()

    def set_setting(self, key, value):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO settings (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """, (key, str(value)))
            conn.commit()
        finally:
            conn.close()

    # --- GOALS & EVENTS CRUD ---
    def add_event(self, name, type_, date, time=None, priority="Medium", description="", prep_topics="", target="", status="Pending"):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO goals_events (name, type, date, time, priority, description, preparation_topics, target, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (name, type_, date, time, priority, description, prep_topics, target, status))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def get_events(self, status=None):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            if status:
                cursor.execute("SELECT * FROM goals_events WHERE status = ? ORDER BY date ASC, time ASC", (status,))
            else:
                cursor.execute("SELECT * FROM goals_events ORDER BY date ASC, time ASC")
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def update_event_status(self, event_id, status):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE goals_events SET status = ? WHERE id = ?", (status, event_id))
            conn.commit()
        finally:
            conn.close()

    def delete_event(self, event_id):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM goals_events WHERE id = ?", (event_id,))
            conn.commit()
        finally:
            conn.close()

    # --- TASKS CRUD ---
    def add_task(self, name, duration_minutes=25, priority="Medium", difficulty="Medium", category=None, status="Pending"):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO tasks (name, duration_minutes, priority, difficulty, category, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (name, duration_minutes, priority, difficulty, category, status))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def get_tasks(self, status=None):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            if status:
                cursor.execute("SELECT * FROM tasks WHERE status = ? ORDER BY id DESC", (status,))
            else:
                cursor.execute("SELECT * FROM tasks ORDER BY id DESC")
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def update_task_status(self, task_id, status):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            completed_at = datetime.now().isoformat() if status == "Completed" else None
            cursor.execute("""
                UPDATE tasks 
                SET status = ?, completed_at = ? 
                WHERE id = ?
            """, (status, completed_at, task_id))
            conn.commit()
        finally:
            conn.close()

    def delete_task(self, task_id):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            conn.commit()
        finally:
            conn.close()

    # --- FOCUS SESSIONS CRUD ---
    def log_focus_session(self, task_id, duration_minutes, completed_minutes, type_, state):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            timestamp = datetime.now().isoformat()
            cursor.execute("""
                INSERT INTO focus_sessions (task_id, duration_minutes, completed_minutes, type, timestamp, state)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (task_id, duration_minutes, completed_minutes, type_, timestamp, state))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def get_focus_sessions(self, limit=100):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM focus_sessions ORDER BY timestamp DESC LIMIT ?", (limit,))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    # --- DISTRACTION LOGS ---
    def log_distraction(self, window_title, app_name=None, session_id=None):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            timestamp = datetime.now().isoformat()
            cursor.execute("""
                INSERT INTO distraction_logs (window_title, app_name, timestamp, session_id)
                VALUES (?, ?, ?, ?)
            """, (window_title, app_name, timestamp, session_id))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def get_distraction_count(self, start_date=None):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            if start_date:
                cursor.execute("SELECT COUNT(*) FROM distraction_logs WHERE timestamp >= ?", (start_date,))
            else:
                cursor.execute("SELECT COUNT(*) FROM distraction_logs")
            return cursor.fetchone()[0]
        finally:
            conn.close()

    # --- SCHEDULE ITEMS CRUD ---
    def add_schedule_item(self, task_name, start_time, duration_minutes, priority, date, status="Pending"):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO schedule_items (task_name, start_time, duration_minutes, priority, date, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (task_name, start_time, duration_minutes, priority, date, status))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def get_schedule_for_date(self, date_str):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM schedule_items WHERE date = ? ORDER BY start_time ASC", (date_str,))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def clear_schedule_for_date(self, date_str):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM schedule_items WHERE date = ?", (date_str,))
            conn.commit()
        finally:
            conn.close()

    def update_schedule_item_status(self, item_id, status):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE schedule_items SET status = ? WHERE id = ?", (status, item_id))
            conn.commit()
        finally:
            conn.close()
