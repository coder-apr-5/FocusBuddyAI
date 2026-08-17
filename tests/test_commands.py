import os
import unittest
import tempfile
from datetime import datetime
from app.database.db import DatabaseManager
from app.core.config import ConfigManager
from app.voice.tts import TTSEngine
from app.focus.timer import FocusTimer
from app.planner.engine import PlannerEngine
from app.core.commands import CommandRouter

class MockTTS:
    def __init__(self):
        self.spoken = []
    def speak(self, text):
        self.spoken.append(text)
    def stop(self):
        pass

class TestCommandRouterLocal(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.db = DatabaseManager(self.db_path)
        self.config = ConfigManager(self.db)
        
        self.tts = MockTTS()
        self.timer = FocusTimer(self.db, self.tts)
        self.planner = PlannerEngine(self.db, self.config)
        self.router = CommandRouter(self.db, self.timer, self.planner, self.tts, None)

    def tearDown(self):
        self.timer.stop()
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_local_timer_controls(self):
        # 1. Start timer
        resp = self.router.route("start 25 minute focus")
        self.assertIn("started", resp.lower())
        self.assertEqual(self.timer.current_state, "Focus")
        
        # 2. Pause timer
        resp = self.router.route("pause timer")
        self.assertIn("paused", resp.lower())
        
        # 3. Resume timer
        resp = self.router.route("resume timer")
        self.assertIn("resuming", resp.lower())
        
        # 4. Stop timer
        resp = self.router.route("stop timer")
        self.assertIn("stopped", resp.lower())
        self.assertEqual(self.timer.current_state, "Idle")

    def test_local_remaining_time(self):
        self.timer.start_focus(25)
        resp = self.router.route("time left")
        self.assertIn("remaining", resp.lower())

    def test_local_complete_next_task(self):
        today_str = datetime.now().strftime("%Y-%m-%d")
        task_id = self.db.add_schedule_item(
            task_name="Write Docstrings",
            start_time="11:30",
            duration_minutes=25,
            priority="Medium",
            date=today_str,
            status="Pending"
        )
        
        resp = self.router.route("complete next task")
        self.assertIn("completed", resp.lower())
        
        # Check database
        schedule = self.db.get_schedule_for_date(today_str)
        self.assertEqual(schedule[0]["status"], "Completed")

    def test_current_time_lookup(self):
        resp = self.router.route("what time is it")
        self.assertIn("currently", resp.lower())
