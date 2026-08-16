import os
import sys
from PySide6.QtCore import QObject, Signal, QTimer
from datetime import datetime, time

# Try importing Windows-specific GUI APIs; fall back gracefully if unavailable
try:
    import win32gui
    import win32process
    import win32con
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

class SchedulerManager(QObject):
    # Signals
    distraction_detected = Signal(str) # Emits distracting window title
    schedule_alert = Signal(str, str) # Emits task_name, start_time
    countdowns_updated = Signal(list) # Emits list of countdown texts

    def __init__(self, db_manager, config_manager, focus_timer, tts_engine):
        super().__init__()
        self.db = db_manager
        self.config = config_manager
        self.focus_timer = focus_timer
        self.tts = tts_engine
        
        # Keep track of last warned window to avoid spamming
        self.last_warned_window = ""
        self.last_checked_minute = -1
        
        # 1-second timer for countdowns and alerts
        self.alert_timer = QTimer(self)
        self.alert_timer.timeout.connect(self._check_schedule_alerts)
        self.alert_timer.start(1000)

        # 2-second timer for window monitoring
        self.monitor_timer = QTimer(self)
        self.monitor_timer.timeout.connect(self._monitor_active_window)
        self.monitor_timer.start(2000)

    def _monitor_active_window(self):
        """Monitors active window. Triggers distraction alert if focus session is active."""
        if not self.config.get("distraction_monitoring", True):
            return

        # Distraction monitoring only triggers when in Focus or Recovery state
        timer_state = self.focus_timer.current_state
        if timer_state not in ["Focus", "Recovery"]:
            return

        if not HAS_WIN32:
            return

        try:
            hwnd = win32gui.GetForegroundWindow()
            if hwnd:
                window_title = win32gui.GetWindowText(hwnd)
                if not window_title:
                    return
                
                # Check if it matches distracting list
                distracting_str = self.config.get("distracting_websites", "")
                keywords = [k.strip().lower() for k in distracting_str.split(",") if k.strip()]
                
                title_lower = window_title.lower()
                is_distracted = any(kw in title_lower for kw in keywords)
                
                if is_distracted:
                    # Filter out FocusBuddy window itself to prevent loop
                    if "focusbuddy" in title_lower:
                        return
                        
                    # Log distraction to DB (limit frequency to once per 10s per window title)
                    if window_title != self.last_warned_window:
                        self.last_warned_window = window_title
                        print(f"[Monitor] Distraction detected: {window_title}")
                        self.db.log_distraction(window_title, session_id=self.focus_timer.current_task_id)
                        
                        # Emit signal for GUI warning
                        self.distraction_detected.emit(window_title)
                        
                        # Optional local sound or TTS warning
                        self.tts.speak("Please return to focus. Let's finish our session.")
        except Exception as e:
            print(f"Error during active window monitoring: {e}")

    def _check_schedule_alerts(self):
        """Checks if a scheduled task is starting at the current minute."""
        now = datetime.now()
        current_minute = now.minute
        
        # Run only once per minute
        if current_minute == self.last_checked_minute:
            return
            
        self.last_checked_minute = current_minute
        
        today_str = now.strftime("%Y-%m-%d")
        now_time_str = now.strftime("%H:%M")
        
        # Check alerts
        schedule = self.db.get_schedule_for_date(today_str)
        for item in schedule:
            if item['status'] == 'Pending' and item['start_time'] == now_time_str:
                print(f"[Alert] Starting task: {item['task_name']}")
                self.schedule_alert.emit(item['task_name'], item['start_time'])
                
                # Voice announcement
                self.tts.speak(f"Time to start {item['task_name']}.")

        # Trigger countdown update signal
        self._update_countdowns()

    def _update_countdowns(self):
        """Calculates countdowns for upcoming events and emits them."""
        events = self.db.get_events(status="Pending")
        countdown_list = []
        
        for event in events:
            try:
                event_date = datetime.strptime(event['date'], "%Y-%m-%d")
                days_left = (event_date - datetime.now()).days + 1
                
                if days_left < 0:
                    status_text = "Passed"
                elif days_left == 0:
                    status_text = "Today"
                elif days_left == 1:
                    status_text = "Tomorrow"
                else:
                    status_text = f"{days_left} days"
                    
                countdown_list.append({
                    "id": event["id"],
                    "name": event["name"],
                    "type": event["type"],
                    "date": event["date"],
                    "countdown": status_text,
                    "priority": event["priority"]
                })
            except Exception as e:
                print(f"Error parsing date for event {event['name']}: {e}")
                
        self.countdowns_updated.emit(countdown_list)

    def apply_website_blocking(self):
        """
        Reversible hosts-file blocker. Maps distracting domains to 127.0.0.1.
        Requires Admin privileges. Falls back to warning overlay if not Admin.
        """
        if not self.config.get("website_blocking", False):
            self.remove_website_blocking()
            return

        hosts_path = r"C:\Windows\System32\drivers\etc\hosts"
        redirect_ip = "127.0.0.1"
        distracting_str = self.config.get("distracting_websites", "")
        domains = [d.strip() for d in distracting_str.split(",") if d.strip()]
        
        block_lines = [f"{redirect_ip} {domain}\n" for domain in domains]
        block_lines.append(f"{redirect_ip} www.{domain}\n" for domain in domains) # Add www. variants
        
        # Flatten list
        flat_lines = []
        for domain in domains:
            flat_lines.append(f"{redirect_ip} {domain}\n")
            if not domain.startswith("www."):
                flat_lines.append(f"{redirect_ip} www.{domain}\n")

        marker = "# --- FOCUSBUDDY BLOCK START ---\n"
        end_marker = "# --- FOCUSBUDDY BLOCK END ---\n"

        try:
            with open(hosts_path, "r") as file:
                content = file.readlines()
            
            # Remove any old FocusBuddy block first
            new_content = []
            skip = False
            for line in content:
                if line == marker:
                    skip = True
                    continue
                if line == end_marker:
                    skip = False
                    continue
                if not skip:
                    new_content.append(line)

            # Append new block
            new_content.append(marker)
            new_content.extend(flat_lines)
            new_content.append(end_marker)

            with open(hosts_path, "w") as file:
                file.writelines(new_content)
            print("[Blocker] Successfully applied website blocking via hosts file.")
        except PermissionError:
            print("[Blocker] Permission denied to write hosts file. Ensure app is run as Administrator. Falling back to overlay warning.")
        except Exception as e:
            print(f"[Blocker] Error applying website blocking: {e}")

    def remove_website_blocking(self):
        """Removes FocusBuddy blocks from the Windows hosts file."""
        hosts_path = r"C:\Windows\System32\drivers\etc\hosts"
        marker = "# --- FOCUSBUDDY BLOCK START ---\n"
        end_marker = "# --- FOCUSBUDDY BLOCK END ---\n"

        try:
            if not os.path.exists(hosts_path):
                return
                
            with open(hosts_path, "r") as file:
                content = file.readlines()
            
            new_content = []
            skip = False
            for line in content:
                if line == marker:
                    skip = True
                    continue
                if line == end_marker:
                    skip = False
                    continue
                if not skip:
                    new_content.append(line)

            with open(hosts_path, "w") as file:
                file.writelines(new_content)
            print("[Blocker] Successfully removed website blocking.")
        except PermissionError:
            print("[Blocker] Permission denied to remove website blocking from hosts file. Ensure app is run as Administrator.")
        except Exception as e:
            print(f"[Blocker] Error removing website blocking: {e}")
