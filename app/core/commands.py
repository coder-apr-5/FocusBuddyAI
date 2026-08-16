import re
from datetime import datetime, timedelta

class CommandRouter:
    def __init__(self, db, timer, planner, tts, ai_provider):
        self.db = db
        self.timer = timer
        self.planner = planner
        self.tts = tts
        self.ai = ai_provider

    def route(self, command_text: str) -> str:
        """
        Parses command_text, runs corresponding logic, speaks output, and returns response string.
        """
        cmd = command_text.strip().lower()
        if not cmd:
            return "Please say or type a command."

        print(f"[CommandRouter] Routing: '{cmd}'")

        # 1. Distracted / Losing Focus
        if any(x in cmd for x in ["distracted", "losing focus", "lose focus", "lost focus"]):
            self.timer.start_recovery_session()
            response = "That's okay. Let's reset. I've started a 10-minute recovery session. Let's work on your current task now."
            self.tts.speak(response)
            return response

        # 2. Stuck
        if "stuck" in cmd:
            # Signal the main window to open Stuck Mode Wizard
            # Handled in GUI via events or custom actions, but return response
            return "__TRIGGER_STUCK_MODE__"

        # 3. Start focus session / Start coding
        focus_match = re.search(r"start (?:a )?(\d+)\s*(?:minute|min)?\s*focus", cmd)
        if focus_match:
            duration = int(focus_match.group(1))
            self.timer.start_focus(duration)
            response = f"Focus session started for {duration} minutes."
            self.tts.speak(response)
            return response
        
        if "start coding" in cmd or "start focus" in cmd:
            self.timer.start_focus(25)
            response = "Focus session started. Let's start coding."
            self.tts.speak(response)
            return response

        # 4. Break
        if "break" in cmd:
            self.timer.start_break(5)
            response = "Take a short break. You've earned it."
            self.tts.speak(response)
            return response

        # 5. What's next / What is my schedule today / What should I study now
        if "next" in cmd or "what should i work on" in cmd or "what should i study now" in cmd:
            next_item = self.planner.get_next_task()
            if next_item:
                response = f"Your next task is {next_item['task_name']} scheduled at {next_item['start_time']}."
            else:
                response = "You have no tasks scheduled next. You can add a new goal or exam to plan."
            self.tts.speak(response)
            return response

        if "schedule today" in cmd or "my schedule" in cmd:
            today_str = datetime.now().strftime("%Y-%m-%d")
            schedule = self.db.get_schedule_for_date(today_str)
            if schedule:
                items = [f"{item['start_time']}: {item['task_name']}" for item in schedule]
                response = "Today's schedule: " + ", ".join(items)
            else:
                response = "Your schedule for today is empty. Would you like me to generate a plan?"
            self.tts.speak(response)
            return response

        # 6. Progress: How am I doing today?
        if any(x in cmd for x in ["how am i doing", "how is my progress", "today's progress", "how am i doing today"]):
            today_str = datetime.now().strftime("%Y-%m-%d")
            schedule = self.db.get_schedule_for_date(today_str)
            completed = sum(1 for item in schedule if item['status'] == 'Completed')
            total = len(schedule)
            
            # Sum focus minutes today
            sessions = self.db.get_focus_sessions(limit=50)
            focus_time = 0
            for s in sessions:
                if s['timestamp'].startswith(today_str) and s['type'] == 'focus':
                    focus_time += s['completed_minutes']
                    
            response = f"You completed {completed} out of {total} tasks today and logged {focus_time} minutes of focus."
            self.tts.speak(response)
            return response

        # 7. Add Exam / Deadline / Project
        # Matches: "I have an exam on September 14" or "exam DBMS on September 14" or "deadline on 2026-09-14"
        event_match = re.search(r"i have (?:an|a) (\w+) on (\w+\s+\d+|\d{4}-\d{2}-\d{2})", cmd)
        if event_match:
            event_type = event_match.group(1).capitalize()
            raw_date = event_match.group(2)
            
            # Simple date parsing logic
            try:
                date_parsed = self._parse_date_string(raw_date)
                self.db.add_event(
                    name=f"New {event_type}",
                    type_=event_type,
                    date=date_parsed.strftime("%Y-%m-%d"),
                    priority="High",
                    description="Added via voice command."
                )
                # Re-generate schedule dynamically
                self.planner.generate_daily_schedule()
                response = f"I've added your {event_type} on {date_parsed.strftime('%B %d')}. I'll update your study plan accordingly."
                self.tts.speak(response)
                return response
            except Exception as e:
                response = f"I found the event date but couldn't parse it. Please specify like September 14."
                return response

        # 8. Postpone / Reschedule: "Move my next task to 7 PM."
        move_match = re.search(r"move my next task to (\d+)\s*(pm|am)?", cmd)
        if move_match:
            hour = int(move_match.group(1))
            ampm = move_match.group(2)
            if ampm == "pm" and hour < 12:
                hour += 12
            elif ampm == "am" and hour == 12:
                hour = 0
            
            time_str = f"{hour:02d}:00"
            success = self.planner.postpone_next_task(time_str)
            if success:
                response = f"I've moved your next task to {time_str}."
            else:
                response = "I couldn't find a task to move."
            self.tts.speak(response)
            return response

        # Default fallback to AI Provider (Natural language support)
        if self.ai:
            response = self.ai.get_response(command_text)
            self.tts.speak(response)
            return response
            
        return "Command not recognized. Try asking 'what's next' or 'start a focus session'."

    def _parse_date_string(self, date_str: str) -> datetime:
        # Check standard format YYYY-MM-DD
        if re.match(r"\d{4}-\d{2}-\d{2}", date_str):
            return datetime.strptime(date_str, "%Y-%m-%d")
        
        # Check Month Day format (e.g. september 14, oct 5)
        # Parse month name
        months = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december",
                  "jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
        
        parts = date_str.split()
        month_idx = -1
        day = 1
        for part in parts:
            if part in months:
                month_idx = months.index(part) % 12 + 1
            elif part.isdigit():
                day = int(part)
        
        if month_idx != -1:
            current_year = datetime.now().year
            # If the date has passed this year, assume next year
            dt = datetime(current_year, month_idx, day)
            if dt < datetime.now() - timedelta(days=1):
                dt = datetime(current_year + 1, month_idx, day)
            return dt
            
        raise ValueError("Unknown date format")
