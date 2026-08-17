import os
import sys
import unittest
import tempfile
from PySide6.QtWidgets import QApplication

app = QApplication.instance() or QApplication([])

from app.database.db import DatabaseManager
from app.core.config import ConfigManager
from app.voice.tts import TTSEngine
from app.focus.timer import FocusTimer
from app.scheduler.manager import SchedulerManager
from app.ui.dialogs.settings_dialog import SettingsDialog

class MockTTS:
    def speak(self, text):
        pass
    def stop(self):
        pass

class TestSettingsDialog(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.db = DatabaseManager(self.db_path)
        self.config = ConfigManager(self.db)
        
        self.tts = MockTTS()
        self.timer = FocusTimer(self.db, self.tts)
        self.scheduler = SchedulerManager(self.db, self.config, self.timer, self.tts)
        
    def tearDown(self):
        self.timer.stop()
        self.scheduler.alert_timer.stop()
        self.scheduler.monitor_timer.stop()
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_settings_saving(self):
        # Instantiate settings dialog
        dialog = SettingsDialog(self.config, self.scheduler)
        
        # Populate new details in widgets
        dialog.name_input.setText("Arnab")
        dialog.hours_input.setValue(6.0)
        dialog.gemini_key_input.setText("gemini-test-key")
        dialog.groq_key_input.setText("groq-test-key")
        dialog.openrouter_key_input.setText("openrouter-test-key")
        dialog.wakeword_chk.setChecked(False)
        
        # Save settings
        dialog.save_settings()
        
        # Verify configurations are persisted in database
        self.assertEqual(self.config.get("user_name"), "Arnab")
        self.assertEqual(float(self.config.get("study_hours")), 6.0)
        self.assertEqual(self.config.get("gemini_api_key"), "gemini-test-key")
        self.assertEqual(self.config.get("groq_api_key"), "groq-test-key")
        self.assertEqual(self.config.get("openrouter_api_key"), "openrouter-test-key")
        self.assertEqual(str(self.config.get("wake_word_enabled")), "False")
