import os
import sys
import unittest
import tempfile
from datetime import datetime, timedelta
from PySide6.QtWidgets import QApplication

# Ensure QApplication exists for PySide6 objects
app = QApplication.instance() or QApplication([])

from app.database.db import DatabaseManager
from app.core.config import ConfigManager
from app.voice.tts import TTSEngine
from app.focus.timer import FocusTimer
from app.planner.engine import PlannerEngine
from app.scheduler.manager import SchedulerManager
from app.notifications.notifier import NotificationManager
from app.core.commands import CommandRouter
from app.core.assistant import AssistantEngine

class MockTTS:
    def __init__(self):
        self.spoken = []
    def speak(self, text):
        self.spoken.append(text)
    def stop(self):
        pass

class MockNotifier:
    def __init__(self):
        self.notifications = []
    def send_notification(self, title, message):
        self.notifications.append((title, message))

class TestAssistantEngine(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.db = DatabaseManager(self.db_path)
        self.config = ConfigManager(self.db)
        
        self.tts = MockTTS()
        self.timer = FocusTimer(self.db, self.tts)
        self.planner = PlannerEngine(self.db, self.config)
        self.scheduler = SchedulerManager(self.db, self.config, self.timer, self.tts)
        self.notifier = MockNotifier()
        self.router = CommandRouter(self.db, self.timer, self.planner, self.tts, None)
        
        self.assistant = AssistantEngine(
            self.db, self.config, self.timer, self.scheduler,
            self.tts, self.notifier, self.planner, self.router
        )

    def tearDown(self):
        self.timer.stop()
        self.scheduler.alert_timer.stop()
        self.scheduler.monitor_timer.stop()
        self.assistant.shutdown()
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_state_transitions(self):
        self.assertEqual(self.assistant.current_state, "IDLE")
        
        # Transition to FOCUS_ACTIVE via FocusTimer
        self.timer.start_focus(25)
        self.assertEqual(self.assistant.current_state, "FOCUS_ACTIVE")
        
        # Transition to BREAK_ACTIVE via FocusTimer
        self.timer.start_break(5)
        self.assertEqual(self.assistant.current_state, "BREAK_ACTIVE")
        
        # Stop timer transitions back to IDLE
        self.timer.stop()
        self.assertEqual(self.assistant.current_state, "IDLE")

    def test_proactive_schedule_alerts(self):
        # Insert a pending schedule item for today starting in exactly 10 minutes
        now = datetime.now()
        target_time = now + timedelta(minutes=10)
        time_str = target_time.strftime("%H:%M")
        today_str = now.strftime("%Y-%m-%d")
        
        task_id = self.db.add_schedule_item(
            task_name="Java Tutorial",
            start_time=time_str,
            duration_minutes=25,
            priority="Medium",
            date=today_str,
            status="Pending"
        )
        
        # Force a ticker check
        self.assistant._check_proactive_schedule()
        
        # Verify state transition to TASK_UPCOMING and speaking alert
        self.assertEqual(self.assistant.current_state, "TASK_UPCOMING")
        self.assertTrue(any("starts in 10 minutes" in text for text in self.tts.spoken))
        self.assertTrue(any("Java Tutorial" in notification[1] for notification in self.notifier.notifications))

    def test_skipped_task_rescheduling(self):
        # Insert a pending schedule item for today starting 31 minutes ago
        now = datetime.now()
        target_time = now - timedelta(minutes=31)
        time_str = target_time.strftime("%H:%M")
        today_str = now.strftime("%Y-%m-%d")
        
        task_id = self.db.add_schedule_item(
            task_name="DBMS Revision",
            start_time=time_str,
            duration_minutes=25,
            priority="High",
            date=today_str,
            status="Pending"
        )
        
        # Force a ticker check
        self.assistant._check_proactive_schedule()
        
        # Verify state transition to TASK_SKIPPED
        self.assertEqual(self.assistant.current_state, "TASK_SKIPPED")
        
        # Check that original task is marked Rescheduled, and a new one is created today
        schedule = self.db.get_schedule_for_date(today_str)
        self.assertEqual(len(schedule), 2)
        
        statuses = [item['status'] for item in schedule]
        self.assertIn("Rescheduled", statuses)
        self.assertIn("Pending", statuses)

