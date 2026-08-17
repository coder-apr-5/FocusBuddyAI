import os
import json
from datetime import datetime

class ContextManager:
    def __init__(self):
        self.conversation_history = [] # Stores last N turns: [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
        self.max_history = 10

    def add_message(self, role: str, content: str):
        """Adds a message to the conversation history and prunes older turns."""
        self.conversation_history.append({
            "role": role,
            "content": content
        })
        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history:]

    def get_context(self, assistant_engine) -> dict:
        """Compiles a compact current context dictionary of the system state."""
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        
        # 1. Retrieve today's schedule
        schedule = assistant_engine.db.get_schedule_for_date(today_str)
        
        # 2. Determine current task and status
        current_task_name = "None"
        task_status = "None"
        
        timer_state = assistant_engine.timer.current_state
        if timer_state in ["Focus", "Recovery"]:
            task_id = assistant_engine.timer.current_task_id
            if task_id:
                for item in schedule:
                    if item['id'] == task_id:
                        current_task_name = item['task_name']
                        task_status = "Active"
                        break
            else:
                current_task_name = "Distraction Recovery Session" if timer_state == "Recovery" else "Unscheduled Study Session"
                task_status = "Active"
        else:
            # Fall back to first overdue or pending task today
            for item in schedule:
                if item['status'] in ['Overdue', 'Pending']:
                    current_task_name = item['task_name']
                    task_status = item['status']
                    break

        # 3. Retrieve next scheduled task
        next_task_item = assistant_engine.planner.get_next_task()
        next_task = next_task_item['task_name'] if next_task_item else "None"
        next_task_time = next_task_item['start_time'] if next_task_item else "None"

        # 4. Retrieve upcoming deadlines & countdowns
        events = assistant_engine.db.get_events(status="Pending")
        upcoming_deadlines = []
        for event in events:
            try:
                event_date = datetime.strptime(event['date'], "%Y-%m-%d")
                days_left = (event_date - now).days + 1
                upcoming_deadlines.append({
                    "name": event['name'],
                    "type": event['type'],
                    "date": event['date'],
                    "days_remaining": max(0, days_left),
                    "topics": event['preparation_topics']
                })
            except Exception:
                continue

        # 5. Compile today's stats
        completed_count = sum(1 for item in schedule if item['status'] == 'Completed')
        total_tasks = len(schedule)
        
        sessions = assistant_engine.db.get_focus_sessions(limit=100)
        focus_minutes = 0
        for s in sessions:
            if s['timestamp'].startswith(today_str) and s['type'] in ['focus', 'recovery']:
                focus_minutes += s['completed_minutes']
                
        distractions = assistant_engine.db.get_distraction_count(start_date=today_str)
        
        today_progress = {
            "completed_tasks": completed_count,
            "total_tasks": total_tasks,
            "focus_minutes": focus_minutes,
            "distractions_count": distractions
        }

        # 6. Focus session timer status
        focus_session = {
            "state": timer_state,
            "session_type": assistant_engine.timer.session_type,
            "time_remaining_seconds": assistant_engine.timer.seconds_remaining,
            "total_duration_minutes": assistant_engine.timer.total_duration_minutes
        }

        # 7. Final Context Document
        context = {
            "current_time": now.strftime("%Y-%m-%d %H:%M"),
            "current_task": current_task_name,
            "task_status": task_status,
            "next_task": next_task,
            "next_task_time": next_task_time,
            "upcoming_deadlines": upcoming_deadlines,
            "today_progress": today_progress,
            "focus_session": focus_session,
            "recent_conversation": self.conversation_history,
            "user_state": assistant_engine.current_state
        }
        return context

    def get_context_json(self, assistant_engine) -> str:
        """Returns the context dictionary compiled as a formatted JSON string."""
        return json.dumps(self.get_context(assistant_engine), indent=2)
