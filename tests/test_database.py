import os
import unittest
import tempfile
from app.database.db import DatabaseManager

class TestDatabase(unittest.TestCase):
    def setUp(self):
        # Create a temporary database file
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.db = DatabaseManager(self.db_path)

    def tearDown(self):
        # Close file descriptor and remove temporary database file
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_settings(self):
        self.db.set_setting("user_name", "TestUser")
        val = self.db.get_setting("user_name")
        self.assertEqual(val, "TestUser")

    def test_add_get_events(self):
        event_id = self.db.add_event(
            name="DBMS Exam",
            type_="Exam",
            date="2026-10-05",
            time="10:00",
            priority="High",
            description="Test exam",
            prep_topics="SQL, Joins",
            target="Grade A"
        )
        self.assertIsNotNone(event_id)
        
        events = self.db.get_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["name"], "DBMS Exam")
        self.assertEqual(events[0]["status"], "Pending")

    def test_update_event_status(self):
        event_id = self.db.add_event(name="Test", type_="Exam", date="2026-10-05")
        self.db.update_event_status(event_id, "Completed")
        
        events = self.db.get_events()
        self.assertEqual(events[0]["status"], "Completed")

    def test_add_get_tasks(self):
        task_id = self.db.add_task(name="Study Arrays", duration_minutes=30, priority="Medium")
        self.assertIsNotNone(task_id)
        
        tasks = self.db.get_tasks()
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["name"], "Study Arrays")
        self.assertEqual(tasks[0]["status"], "Pending")

    def test_update_task_status(self):
        task_id = self.db.add_task(name="Study Lists")
        self.db.update_task_status(task_id, "Completed")
        
        tasks = self.db.get_tasks()
        self.assertEqual(tasks[0]["status"], "Completed")
        self.assertIsNotNone(tasks[0]["completed_at"])
