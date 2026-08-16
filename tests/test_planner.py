import os
import unittest
import tempfile
from datetime import datetime
from app.database.db import DatabaseManager
from app.core.config import ConfigManager
from app.planner.engine import PlannerEngine

class TestPlanner(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.db = DatabaseManager(self.db_path)
        self.config = ConfigManager(self.db)
        self.planner = PlannerEngine(self.db, self.config)

    def tearDown(self):
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_schedule_generation(self):
        # Configure study hours to 2.0 (should produce 4 slots of 30 minutes)
        self.config.set("study_hours", "2.0")
        
        # Add an exam event with preparation topics
        self.db.add_event(
            name="DBMS Exam",
            type_="Exam",
            date="2026-10-05",
            prep_topics="SQL, Joins"
        )
        
        # Add some general tasks
        self.db.add_task(name="Complete Assignment", priority="High")
        
        # Generate schedule
        self.planner.generate_daily_schedule()
        
        # Check generated items
        today_str = datetime.now().strftime("%Y-%m-%d")
        schedule = self.db.get_schedule_for_date(today_str)
        
        # Should generate 4 slots (2.0 hours * 2 slots/hour)
        self.assertEqual(len(schedule), 4)
        
        # First slots should prioritize preparation topics from the exam
        self.assertTrue(any("SQL" in item["task_name"] or "Joins" in item["task_name"] for item in schedule))
        self.assertTrue(any("Complete Assignment" in item["task_name"] for item in schedule))
