import os
import sys
import unittest
import tempfile
from datetime import datetime
# pyrefly: ignore [missing-import]
from PySide6.QtWidgets import QApplication

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
    def send_notification(self, title, message):
        pass

class TestStressRecovery(unittest.TestCase):
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
        import time
        time.sleep(0.2)
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_focus_completion_stress_trigger(self):
        # 1. Simulate Focus timer completing
        self.assistant._on_timer_session_completed("Focus", 25)
        
        # Verify transition to CONVERSATION_MODE and vocal prompts
        self.assertEqual(self.assistant.current_state, "CONVERSATION_MODE")
        self.assertTrue(any("stressed" in text.lower() for text in self.tts.spoken))
        
        # 2. Simulate user responding that they are stressed
        resp = self.router.route("i feel stressed")
        self.assertIn("stress recovery break", resp.lower())
        
        # Verify 10-minute break timer was started
        self.assertEqual(self.timer.current_state, "Break")
        self.assertEqual(self.timer.total_duration_minutes, 10)

    def test_easiest_task_recovery_suggestion(self):
        # Insert tasks of different priorities today
        today_str = datetime.now().strftime("%Y-%m-%d")
        self.db.add_schedule_item(
            task_name="Hard Math Revision",
            start_time="14:00",
            duration_minutes=25,
            priority="High",
            date=today_str,
            status="Pending"
        )
        self.db.add_schedule_item(
            task_name="Clean Study Desk",
            start_time="14:30",
            duration_minutes=15,
            priority="Low",
            date=today_str,
            status="Pending"
        )
        
        # Simulate 10-minute break completing
        self.assistant._on_timer_session_completed("Break", 10)
        
        # Verify it suggested the easiest task: "Clean Study Desk" (priority "Low")
        self.assertTrue(any("Clean Study Desk" in text for text in self.tts.spoken))
        self.assertEqual(self.assistant.current_state, "IDLE")
