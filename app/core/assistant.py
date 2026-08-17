import os
import sys
from datetime import datetime, timedelta
from PySide6.QtCore import QObject, Signal, QTimer, Slot, Qt, QMetaObject, Q_ARG
from app.core.context import ContextManager
from app.voice.wake_word import WakeWordThread

class AssistantEngine(QObject):
    # Signals for the GUI
    state_changed = Signal(str)          # E.g., IDLE, FOCUS_ACTIVE, BREAK_ACTIVE, CONVERSATION_MODE
    gui_status_changed = Signal(str)     # Ready, Listening, Thinking, Speaking, Focus Active, In Conversation
    log_added = Signal(str, str)         # timestamp, log_message
    timer_updated = Signal(int, int, float) # minutes, seconds, progress
    countdowns_updated = Signal(list)    # list of countdowns
    response_emitted = Signal(str)       # text response to display/speak
    schedule_updated = Signal()          # triggers schedule UI refresh
    stuck_wizard_triggered = Signal()    # triggers the Stuck Mode wizard dialog

    def __init__(self, db, config, timer, scheduler, tts, notifier, planner, command_router):
        super().__init__()
        self.db = db
        self.config = config
        self.timer = timer
        self.scheduler = scheduler
        self.tts = tts
        self.notifier = notifier
        self.planner = planner
        self.router = command_router
        self.ai = None # Set later if needed
        self.context_manager = ContextManager()
        
        # State Machine
        self.current_state = "IDLE"  # IDLE, FOCUS_ACTIVE, BREAK_ACTIVE, TASK_UPCOMING, TASK_DUE, TASK_OVERDUE, TASK_SKIPPED, USER_STUCK, USER_DISTRACTED, RECOVERY_MODE, CONVERSATION_MODE, QUIET_MODE
        
        # Tracking alerts & reminders
        self.spoken_reminders = {}   # task_id -> list of reminders already spoken (e.g. ["10m", "5m", "start", "grace_5m", "overdue_15m", "skipped_30m"])
        self.last_checked_minute = -1
        
        # Conversation Timer (Silence timeout)
        self.conversation_timer = QTimer(self)
        self.conversation_timer.timeout.connect(self._on_conversation_timeout)
        self.conversation_timer.setSingleShot(True)
        
        # Engine ticker running every 1 second
        self.ticker = QTimer(self)
        self.ticker.timeout.connect(self._on_tick)
        self.ticker.start(1000)
        
        # Background Wake Word Thread
        self.wake_word_thread = WakeWordThread(self.config)
        self.wake_word_thread.wake_word_detected.connect(self._on_wake_word_detected)
        self.wake_word_thread.start()
        
        # Connect to sub-module signals
        self._connect_signals()
        
        self.add_log("System", "Assistant Engine initialized successfully.")

    def _connect_signals(self):
        # Focus Timer Signals
        self.timer.tick.connect(self._on_timer_tick)
        self.timer.state_changed.connect(self._on_timer_state_changed)
        self.timer.session_completed.connect(self._on_timer_session_completed)
        
        # Scheduler Signals
        self.scheduler.distraction_detected.connect(self._on_distraction_detected)
        self.scheduler.countdowns_updated.connect(self._on_countdowns_updated)

    def set_state(self, new_state):
        if self.current_state != new_state:
            old_state = self.current_state
            self.add_log("State", f"Transitioned from {old_state} to {new_state}")
            self.current_state = new_state
            self.state_changed.emit(new_state)
            self._update_gui_status()
            
            # Pause wake-word thread when recording in conversation mode, resume when active session ends
            if new_state == "CONVERSATION_MODE":
                self.wake_word_thread.pause_listening()
            elif old_state == "CONVERSATION_MODE" and new_state in ["IDLE", "FOCUS_ACTIVE", "BREAK_ACTIVE"]:
                self.wake_word_thread.resume_listening()

    def _on_wake_word_detected(self):
        if self.current_state not in ["CONVERSATION_MODE", "USER_STUCK"]:
            self._speak_and_log("System", "Yes? I'm listening.", state="CONVERSATION_MODE")
            self._trigger_conversational_listening("Yes? I'm listening.")

    def shutdown(self):
        self.ticker.stop()
        self.conversation_timer.stop()
        self.wake_word_thread.stop()

    def _update_gui_status(self):
        """Maps internal Assistant State to user-facing GUI status."""
        status_map = {
            "IDLE": "Ready",
            "FOCUS_ACTIVE": "Focus Active",
            "BREAK_ACTIVE": "Ready",
            "TASK_UPCOMING": "Ready",
            "TASK_DUE": "Ready",
            "TASK_OVERDUE": "Ready",
            "TASK_SKIPPED": "Ready",
            "USER_STUCK": "Ready",
            "USER_DISTRACTED": "Ready",
            "RECOVERY_MODE": "Focus Active",
            "CONVERSATION_MODE": "In Conversation",
            "QUIET_MODE": "Ready"
        }
        self.gui_status_changed.emit(status_map.get(self.current_state, "Ready"))

    def add_log(self, category, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_added.emit(timestamp, f"[{category}] {message}")

    def _speak_and_log(self, category, text, state=None):
        self.tts.speak(text)
        self.add_log(category, text)
        self.response_emitted.emit(text)
        self.context_manager.add_message("assistant", text)
        if state:
            self.set_state(state)

    # --- VOICE WORKFLOWS ---
    def trigger_voice_input(self):
        """Activates PTT / Wake word conversation mode."""
        self.set_state("CONVERSATION_MODE")
        self.gui_status_changed.emit("Listening")
        self.add_log("Voice", "Listening for voice input...")
        
        from app.voice.stt import STTEngine
        stt = STTEngine(self.config)
        stt.listen_and_transcribe(self._handle_stt_result)

    def _handle_stt_result(self, text, success):
        QMetaObject.invokeMethod(self, "_process_stt_result_on_main",
                                 Qt.ConnectionType.QueuedConnection,
                                 Q_ARG(str, text),
                                 Q_ARG(bool, success))

    @Slot(str, bool)
    def _process_stt_result_on_main(self, text, success):
        if not success:
            self.add_log("Voice Error", text)
            # If the error is a service error or microphone missing error, do not retry, just exit
            if any(x in text.lower() for x in ["unavailable", "no microphone", "error"]):
                self._update_gui_status()
                if self.current_state == "CONVERSATION_MODE":
                    self.set_state("IDLE")
                return
            
            # If it's just a silence or understanding error, speak the retry prompt and listen again!
            if self.current_state == "CONVERSATION_MODE":
                self.tts.speak(text)
                self.add_log("Assistant", text)
                self.response_emitted.emit(text)
                self.conversation_timer.start(7000)
                self.gui_status_changed.emit("In Conversation")
                self._trigger_conversational_listening(text)
            else:
                self._update_gui_status()
            return
            
        self.context_manager.add_message("user", text)
        self.add_log("User Input", f'"{text}"')
        self.gui_status_changed.emit("Thinking")
        
        # Route the command with compiled context
        context_json = self.context_manager.get_context_json(self)
        response = self.router.route(text, context_json)
        
        self.gui_status_changed.emit("Speaking")
        if response == "__TRIGGER_STUCK_MODE__":
            self.context_manager.add_message("assistant", "Triggered Stuck Mode.")
            self.add_log("Assistant", "Triggering Stuck Recovery Mode.")
            self.set_state("USER_STUCK")
            self.stuck_wizard_triggered.emit()
        else:
            self.context_manager.add_message("assistant", response)
            self.add_log("Assistant", response)
            self.response_emitted.emit(response)
            
            # Keep conversation alive: restart 7-second silence timeout
            if self.current_state == "CONVERSATION_MODE":
                self.conversation_timer.start(7000)
                self.gui_status_changed.emit("In Conversation")
                self._trigger_conversational_listening(response)

    def _trigger_conversational_listening(self, response_text):
        # Calculate speaking duration (160 words/min = 2.67 words/sec)
        words = len(response_text.split())
        seconds = (words / 2.67) + 1.2
        QTimer.singleShot(int(seconds * 1000), self._start_listening_slot)

    @Slot()
    def _start_listening_slot(self):
        if self.current_state == "CONVERSATION_MODE":
            from app.voice.stt import STTEngine
            stt = STTEngine(self.config)
            stt.listen_and_transcribe(self._handle_stt_result)
            self.gui_status_changed.emit("Listening")
            self.conversation_timer.start(7000)

    def _on_conversation_timeout(self):
        if self.current_state == "CONVERSATION_MODE":
            self.add_log("Voice", "Conversation timed out due to silence.")
            self.set_state("IDLE")
            self.tts.speak("Goodbye. Feel free to speak to me again when you need support.")

    # --- TIMER SIGNALS INTERACTION ---
    def _on_timer_tick(self, minutes, seconds, progress):
        self.timer_updated.emit(minutes, seconds, progress)

    def _on_timer_state_changed(self, timer_state):
        if timer_state == "Focus":
            self.set_state("FOCUS_ACTIVE")
        elif timer_state == "Break":
            self.set_state("BREAK_ACTIVE")
        elif timer_state == "Recovery":
            self.set_state("RECOVERY_MODE")
        elif timer_state == "Idle":
            self.set_state("IDLE")

    def _on_timer_session_completed(self, session_type, duration_minutes):
        self.add_log("Timer", f"Completed {session_type} session of {duration_minutes} minutes.")
        self.schedule_updated.emit()
        self.notifier.send_notification(
            title="Session Complete!",
            message=f"Your {session_type} session of {duration_minutes} minutes has finished."
        )
        
        if session_type == "Focus":
            prompt = "Focus session completed! Great job. How are you feeling? If you're feeling stressed, we can do a ten-minute recovery break."
            self._speak_and_log("System", prompt, state="CONVERSATION_MODE")
            self._trigger_conversational_listening(prompt)

    # --- SCHEDULER SIGNALS INTERACTION ---
    def _on_distraction_detected(self, window_title):
        self.add_log("Distraction", f"User distracted by '{window_title}'")
        self.set_state("USER_DISTRACTED")

    def _on_countdowns_updated(self, countdown_list):
        self.countdowns_updated.emit(countdown_list)

    # --- ENGINE TICK ACTION ---
    def _on_tick(self):
        """Ticks every second. Performs schedule notifications and grace checks."""
        self._check_proactive_schedule()

    def _check_proactive_schedule(self):
        # Bypass alerts if quiet hours or quiet mode is enabled
        if self.config.get("quiet_mode", False):
            return
            
        now = datetime.now()
        current_minute = now.minute
        
        # We check schedule items for today
        today_str = now.strftime("%Y-%m-%d")
        schedule = self.db.get_schedule_for_date(today_str)
        
        for item in schedule:
            task_id = item['id']
            task_name = item['task_name']
            start_time_str = item['start_time'] # "HH:MM"
            status = item['status']
            
            try:
                sh, sm = map(int, start_time_str.split(":"))
                start_dt = now.replace(hour=sh, minute=sm, second=0, microsecond=0)
            except Exception:
                continue
                
            now_stripped = now.replace(second=0, microsecond=0)
            time_diff = (start_dt - now_stripped).total_seconds()
            
            if task_id not in self.spoken_reminders:
                self.spoken_reminders[task_id] = []
                
            # 1. 10 minutes before: TASK_UPCOMING
            if 570 <= time_diff <= 600 and "10m" not in self.spoken_reminders[task_id]:
                if status == "Pending":
                    self.spoken_reminders[task_id].append("10m")
                    self._speak_and_log("Upcoming", f"Your task {task_name} starts in 10 minutes.", state="TASK_UPCOMING")
                    self.notifier.send_notification("Task Upcoming", f"Your task {task_name} starts in 10 minutes.")
                    
            # 2. 5 minutes before: TASK_UPCOMING
            elif 270 <= time_diff <= 300 and "5m" not in self.spoken_reminders[task_id]:
                if status == "Pending":
                    self.spoken_reminders[task_id].append("5m")
                    self._speak_and_log("Upcoming", f"Your task {task_name} starts in 5 minutes.", state="TASK_UPCOMING")
                    self.notifier.send_notification("Task Upcoming", f"Your task {task_name} starts in 5 minutes.")
                    
            # 3. Exact start time: TASK_DUE
            elif -30 <= time_diff <= 30 and "start" not in self.spoken_reminders[task_id]:
                if status == "Pending":
                    self.spoken_reminders[task_id].append("start")
                    self._speak_and_log("Alert", f"It's {start_time_str}. Time to start {task_name}.", state="TASK_DUE")
                    self.notifier.send_notification("Task Starting", f"It is time to start {task_name}.")
                    
            # 4. Grace Period: 5 minutes after start (if not started)
            elif -330 <= time_diff <= -270 and "grace_5m" not in self.spoken_reminders[task_id]:
                if status == "Pending" and self.current_state != "FOCUS_ACTIVE":
                    self.spoken_reminders[task_id].append("grace_5m")
                    self._speak_and_log("Reminder", f"Your scheduled session for {task_name} started five minutes ago. Would you like to start now or reschedule it?", state="TASK_DUE")
                    
            # 5. Overdue warning: 15 minutes after start
            elif -930 <= time_diff <= -870 and "overdue_15m" not in self.spoken_reminders[task_id]:
                if status == "Pending" and self.current_state != "FOCUS_ACTIVE":
                    self.spoken_reminders[task_id].append("overdue_15m")
                    self.db.update_schedule_item_status(task_id, "Overdue")
                    self._speak_and_log("Warning", f"Your task {task_name} is now overdue.", state="TASK_OVERDUE")
                    self.schedule_updated.emit()
                    
            # 6. Skipped check: 30 minutes after start
            elif time_diff <= -1800 and "skipped_30m" not in self.spoken_reminders[task_id]:
                if status in ["Pending", "Overdue"] and self.current_state != "FOCUS_ACTIVE":
                    self.spoken_reminders[task_id].append("skipped_30m")
                    self.db.update_schedule_item_status(task_id, "Skipped")
                    self.set_state("TASK_SKIPPED")
                    
                    # Proactive reschedule warning
                    self._speak_and_log("Alert", f"You missed your scheduled task: {task_name}. Let's reschedule it for later.", state="TASK_SKIPPED")
                    
                    # Call dynamic rescheduling heuristics
                    self.planner.reschedule_task(task_id)
                    self.schedule_updated.emit()
