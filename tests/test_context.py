import os
import sys
import unittest
import tempfile
from datetime import datetime, timedelta
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
from app.core.context import ContextManager

class MockTTS:
    def speak(self, text):
        pass
    def stop(self):
        pass

class MockNotifier:
    def send_notification(self, title, message):
        pass

class TestContextManager(unittest.TestCase):
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
        self.context_manager = ContextManager()

    def tearDown(self):
        self.timer.stop()
        self.scheduler.alert_timer.stop()
        self.scheduler.monitor_timer.stop()
        self.assistant.shutdown()
        import time
        time.sleep(0.2)
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_context_compiling(self):
        # Add event
        self.db.add_event(
            name=" DBMS Assessment",
            type_="Exam",
            date="2026-12-14",
            prep_topics="Queries"
        )
        
        # Add schedule item
        today_str = datetime.now().strftime("%Y-%m-%d")
        self.db.add_schedule_item(
            task_name="Java Prep",
            start_time="10:00",
            duration_minutes=25,
            priority="Medium",
            date=today_str,
            status="Pending"
        )
        
        # Simulate conversation history
        self.context_manager.add_message("user", "how is my progress?")
        self.context_manager.add_message("assistant", "You have completed 0 tasks.")
        
        context = self.context_manager.get_context(self.assistant)
        
        self.assertIn("current_time", context)
        self.assertEqual(context["user_state"], "IDLE")
        self.assertEqual(len(context["recent_conversation"]), 2)
        
        # Check upcoming deadlines list
        deadlines = context["upcoming_deadlines"]
        self.assertTrue(any("DBMS" in d["name"] for d in deadlines))
        
        # Check formatted json
        json_str = self.context_manager.get_context_json(self.assistant)
        self.assertIn('"user_state": "IDLE"', json_str)
