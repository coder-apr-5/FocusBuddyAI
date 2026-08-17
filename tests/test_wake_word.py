import os
import sys
import unittest
import tempfile
from PySide6.QtCore import QCoreApplication

app = QCoreApplication.instance() or QCoreApplication([])

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

class TestWakeWordEngine(unittest.TestCase):
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

    def test_wake_word_trigger_wakeup(self):
        self.assertEqual(self.assistant.current_state, "IDLE")
        
        # Simulate background wake word signal emission
        self.assistant._on_wake_word_detected()
        
        # Should transition to CONVERSATION_MODE and speak wakeup phrase
        self.assertEqual(self.assistant.current_state, "CONVERSATION_MODE")
        self.assertTrue(any("listening" in text.lower() for text in self.tts.spoken))
        
        # Verify wake-word thread is paused when in CONVERSATION_MODE
        self.assertTrue(self.assistant.wake_word_thread._paused)
        
        # Transition back to IDLE should resume it
        self.assistant.set_state("IDLE")
        self.assertFalse(self.assistant.wake_word_thread._paused)
