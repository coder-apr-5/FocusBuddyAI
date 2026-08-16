from PySide6.QtCore import QObject, Signal, QTimer
from datetime import datetime

class FocusTimer(QObject):
    # Signals to communicate with the GUI
    tick = Signal(int, int, float) # minutes, seconds, progress_fraction
    session_completed = Signal(str, int) # session_type (focus/break/recovery), duration_minutes
    state_changed = Signal(str) # "Idle", "Focus", "Break", "Recovery", "Paused"

    def __init__(self, db_manager, tts_engine):
        super().__init__()
        self.db = db_manager
        self.tts = tts_engine
        
        # State variables
        self.current_state = "Idle"
        self.session_type = "focus" # focus, break, recovery
        self.total_duration_minutes = 25
        self.seconds_remaining = 0
        self.current_task_id = None
        self.completed_minutes = 0
        
        # Qt Timer setup
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._on_tick)
        self.timer.setInterval(1000) # Tick every 1 second

    def start_focus(self, duration_minutes=25, task_id=None):
        self.session_type = "focus"
        self.current_task_id = task_id
        self.total_duration_minutes = duration_minutes
        self.seconds_remaining = duration_minutes * 60
        self.current_state = "Focus"
        self.completed_minutes = 0
        
        self.timer.start()
        self.state_changed.emit(self.current_state)
        self.tts.speak("Focus session started. Let's stay focused.")

    def start_break(self, duration_minutes=5):
        self.session_type = "break"
        self.current_task_id = None
        self.total_duration_minutes = duration_minutes
        self.seconds_remaining = duration_minutes * 60
        self.current_state = "Break"
        
        self.timer.start()
        self.state_changed.emit(self.current_state)
        self.tts.speak("Focus session complete. Take a short break.")

    def start_recovery_session(self):
        """Starts a 10-minute distraction recovery session."""
        self.session_type = "recovery"
        self.total_duration_minutes = 10
        self.seconds_remaining = 10 * 60
        self.current_state = "Recovery"
        self.completed_minutes = 0
        
        self.timer.start()
        self.state_changed.emit(self.current_state)
        self.tts.speak("Let's reset. Starting a ten minute recovery session. Focus on the current task.")

    def pause(self):
        if self.current_state in ["Focus", "Break", "Recovery"]:
            self.timer.stop()
            self.current_state = "Paused"
            self.state_changed.emit(self.current_state)
            self.tts.speak("Timer paused.")

    def resume(self):
        if self.current_state == "Paused":
            self.current_state = "Focus" if self.session_type == "focus" else ("Break" if self.session_type == "break" else "Recovery")
            self.timer.start()
            self.state_changed.emit(self.current_state)
            self.tts.speak("Resuming focus.")

    def stop(self):
        self.timer.stop()
        
        # Log partial focus sessions if it was interrupted
        if self.current_state in ["Focus", "Recovery"] and self.completed_minutes > 0:
            self.db.log_focus_session(
                task_id=self.current_task_id,
                duration_minutes=self.total_duration_minutes,
                completed_minutes=self.completed_minutes,
                type_=self.session_type,
                state="Interrupted"
            )
            
        self.current_state = "Idle"
        self.seconds_remaining = 0
        self.state_changed.emit(self.current_state)
        self.tick.emit(0, 0, 0.0)

    def _on_tick(self):
        if self.seconds_remaining > 0:
            self.seconds_remaining -= 1
            
            # Compute completed minutes
            elapsed_seconds = (self.total_duration_minutes * 60) - self.seconds_remaining
            self.completed_minutes = elapsed_seconds // 60
            
            # Emit tick signal
            progress = elapsed_seconds / (self.total_duration_minutes * 60)
            minutes = self.seconds_remaining // 60
            seconds = self.seconds_remaining % 60
            self.tick.emit(minutes, seconds, progress)
            
            # Announce remaining time if configured (e.g. 5 minutes remaining in Focus Mode)
            if self.session_type == "focus" and minutes == 5 and seconds == 0:
                self.tts.speak("Five minutes remaining.")
        else:
            self.timer.stop()
            
            # Log session completion
            state = "Completed"
            self.db.log_focus_session(
                task_id=self.current_task_id,
                duration_minutes=self.total_duration_minutes,
                completed_minutes=self.total_duration_minutes,
                type_=self.session_type,
                state=state
            )
            
            old_type = self.session_type
            old_duration = self.total_duration_minutes
            self.current_state = "Idle"
            self.state_changed.emit(self.current_state)
            
            # Notify completion
            self.session_completed.emit(old_type, old_duration)
            
            if old_type == "focus" or old_type == "recovery":
                # Automatically trigger a break or announce
                self.tts.speak("Focus session complete. Great job! Take a short break.")
            elif old_type == "break":
                self.tts.speak("Break complete. Let's get back to work.")
