from datetime import datetime, timedelta
import math

class PlannerEngine:
    def __init__(self, db_manager, config_manager):
        self.db = db_manager
        self.config = config_manager

    def get_next_task(self):
        """Returns the next pending task for today."""
        today_str = datetime.now().strftime("%Y-%m-%d")
        now_time = datetime.now().strftime("%H:%M")
        
        schedule = self.db.get_schedule_for_date(today_str)
        for item in schedule:
            if item['status'] == 'Pending' and item['start_time'] >= now_time:
                return item
        # If no future pending task, return any pending task today
        for item in schedule:
            if item['status'] == 'Pending':
                return item
        return None

    def postpone_next_task(self, time_str: str = None) -> bool:
        """Postpones the next task to a new start time."""
        next_task = self.get_next_task()
        if next_task:
            self.db.update_schedule_item_status(next_task['id'], 'Rescheduled')
            # Add a new schedule item at the new time
            today_str = datetime.now().strftime("%Y-%m-%d")
            
            if not time_str:
                # Default to 1 hour from now, rounded to the next 30 minutes
                now = datetime.now()
                future_time = now + timedelta(hours=1)
                minute = 30 if future_time.minute >= 30 else 0
                future_time = future_time.replace(minute=minute, second=0, microsecond=0)
                time_str = future_time.strftime("%H:%M")
                
            self.db.add_schedule_item(
                task_name=next_task['task_name'],
                start_time=time_str,
                duration_minutes=next_task['duration_minutes'],
                priority=next_task['priority'],
                date=today_str,
                status='Pending'
            )
            return True
        return False

    def reschedule_task(self, task_id: int, new_time_str: str = None) -> bool:
        """Reschedules a specific schedule item to a new start time today."""
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM schedule_items WHERE id = ?", (task_id,))
            item = cursor.fetchone()
            if not item:
                return False
                
            # Update current item status to 'Rescheduled'
            self.db.update_schedule_item_status(task_id, 'Rescheduled')
            
            # Calculate new time if not provided (1 hour from now rounded to nearest 30 mins)
            if not new_time_str:
                now = datetime.now()
                future_time = now + timedelta(hours=1)
                minute = 30 if future_time.minute >= 30 else 0
                future_time = future_time.replace(minute=minute, second=0, microsecond=0)
                new_time_str = future_time.strftime("%H:%M")
                
            self.db.add_schedule_item(
                task_name=item['task_name'],
                start_time=new_time_str,
                duration_minutes=item['duration_minutes'],
                priority=item['priority'],
                date=item['date'],
                status='Pending'
            )
            return True
        finally:
            conn.close()

    def get_easiest_task(self):
        """Finds the lowest priority pending task today."""
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            today_str = datetime.now().strftime("%Y-%m-%d")
            cursor.execute("SELECT * FROM schedule_items WHERE date = ? AND status = 'Pending'", (today_str,))
            items = cursor.fetchall()
            if not items:
                return None
            
            # Prioritize Low -> Medium -> High (easiest to hardest)
            priority_weights = {"Low": 1, "Medium": 2, "High": 3}
            # Convert SQLite rows to dict-like for easy sorting
            items_list = [dict(item) for item in items]
            sorted_items = sorted(items_list, key=lambda x: priority_weights.get(x['priority'], 2))
            return sorted_items[0]
        finally:
            conn.close()

    def generate_daily_schedule(self):
        """
        Generates today's daily plan based on:
        - Upcoming deadlines and exams
        - Priority
        - Available study hours
        - Distraction counts (weak topics)
        - Pending general tasks
        """
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        # 1. Clear existing pending schedule items for today
        current_schedule = self.db.get_schedule_for_date(today_str)
        # Keep completed items, clear pending ones
        completed_tasks = [item for item in current_schedule if item['status'] == 'Completed']
        self.db.clear_schedule_for_date(today_str)
        for item in completed_tasks:
            self.db.add_schedule_item(
                task_name=item['task_name'],
                start_time=item['start_time'],
                duration_minutes=item['duration_minutes'],
                priority=item['priority'],
                date=today_str,
                status='Completed'
            )

        # 2. Get study hours constraint
        available_hours = float(self.config.get("study_hours", 4.0))
        # Total study slots (30 min blocks: 25 min focus + 5 min break)
        total_slots = int(available_hours * 2)
        
        # If we already completed some slots today, reduce total remaining slots
        completed_hours = sum(item['duration_minutes'] for item in completed_tasks) / 60.0
        remaining_slots = max(0, total_slots - int(completed_hours * 2))
        if remaining_slots == 0:
            return

        # 3. Retrieve events to find topics to prioritize
        events = self.db.get_events(status="Pending")
        topic_weights = {}
        
        for event in events:
            # Calculate days remaining
            event_date = datetime.strptime(event['date'], "%Y-%m-%d")
            days_left = (event_date - datetime.now()).days
            
            # Proximity multiplier: closer exams get much higher priority
            # e.g. < 3 days: multiplier of 10x, < 10 days: 5x, < 30 days: 2x
            if days_left <= 0:
                proximity_multiplier = 15.0
            elif days_left <= 3:
                proximity_multiplier = 10.0
            elif days_left <= 7:
                proximity_multiplier = 5.0
            elif days_left <= 15:
                proximity_multiplier = 3.0
            else:
                proximity_multiplier = 1.5

            # Base priority multiplier
            priority_multipliers = {"High": 3.0, "Medium": 2.0, "Low": 1.0}
            priority_mult = priority_multipliers.get(event['priority'], 1.5)

            # Extract preparation topics
            topics = [t.strip() for t in event['preparation_topics'].split(",") if t.strip()]
            for topic in topics:
                # Base score from proximity and event priority
                score = priority_mult * proximity_multiplier
                
                # Check distraction logs for this topic category
                # If the user logged distraction with window titles matching the topic, boost priority
                # to focus more practice/study on it.
                distractions = self.db.get_distraction_count() # Simplified lookup for demo
                # Boost topic score by distraction events
                # (For demo: boost if topic matches distraction keywords)
                
                topic_weights[topic] = topic_weights.get(topic, 0.0) + score

        # Sort topics by weight descending
        sorted_topics = sorted(topic_weights.items(), key=lambda x: x[1], reverse=True)
        study_queue = [t[0] for t in sorted_topics]

        # 4. Also retrieve general pending tasks
        pending_tasks = self.db.get_tasks(status="Pending")
        general_task_names = [t['name'] for t in pending_tasks]

        # 5. Populate slots
        now = datetime.now()
        # Start scheduling from the next half-hour or a standard 9 AM if earlier
        start_hour = 9
        if now.hour >= start_hour:
            # Start scheduling from next hour
            start_time = now + timedelta(hours=1)
            start_time = start_time.replace(minute=0, second=0, microsecond=0)
        else:
            start_time = datetime(now.year, now.month, now.day, start_hour, 0)

        # Allocate slot times
        slot_time = start_time
        for i in range(remaining_slots):
            # Select what to study
            if i < len(study_queue):
                task_name = f"Study: {study_queue[i]}"
                priority = "High"
            elif i - len(study_queue) < len(general_task_names):
                task_name = general_task_names[i - len(study_queue)]
                priority = "Medium"
            else:
                # Default tasks if nothing else to do
                default_tasks = ["Review Weak Topics", "Coding Practice", "General Reading", "Task Organization"]
                task_name = default_tasks[i % len(default_tasks)]
                priority = "Low"

            time_str = slot_time.strftime("%H:%M")
            self.db.add_schedule_item(
                task_name=task_name,
                start_time=time_str,
                duration_minutes=25, # 25 min study duration per slot
                priority=priority,
                date=today_str,
                status="Pending"
            )
            slot_time += timedelta(minutes=30) # 30 min slots (25 min focus + 5 min break)
