from datetime import datetime
import os
import sys
# pyrefly: ignore [missing-import]
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QListWidget, QListWidgetItem, 
                             QProgressBar, QLineEdit, QSystemTrayIcon, QMenu,
                             QMessageBox, QFrame, QGridLayout, QCheckBox, QStyle,
                             QDialog)
# pyrefly: ignore [missing-import]
from PySide6.QtCore import Qt, QSize, Slot
# pyrefly: ignore [missing-import]
from PySide6.QtGui import QIcon, QAction

from app.ui.styles import MODERN_DARK_STYLESHEET
from app.ui.dialogs.event_dialog import EventDialog
from app.ui.dialogs.settings_dialog import SettingsDialog
from app.ui.widgets.stuck_widget import StuckWidget

class MainWindow(QMainWindow):
    def __init__(self, assistant):
        super().__init__()
        self.assistant = assistant
        self.db = assistant.db
        self.config = assistant.config
        self.timer = assistant.timer
        self.scheduler = assistant.scheduler
        self.tts = assistant.tts
        self.notifier = assistant.notifier
        self.router = assistant.router
        self.ai = assistant.ai
        
        self.setWindowTitle("FocusBuddy AI")
        self.setMinimumSize(950, 650)
        
        # Load stylesheet
        self.setStyleSheet(MODERN_DARK_STYLESHEET)
        
        # UI Setup
        self.init_ui()
        self.init_tray()
        self.connect_signals()
        
        # Initial refresh
        self.refresh_dashboard()

    def init_ui(self):
        # Central widget
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        
        main_layout = QHBoxLayout(self.central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # LEFT COLUMN - Navigation & Branding (Sidebar)
        sidebar = QFrame(self)
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(200)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(10, 20, 10, 20)
        
        # Brand Logo
        logo = QLabel("FOCUSBUDDY", sidebar)
        logo.setObjectName("HeaderLogo")
        logo.setStyleSheet("font-size: 20px; font-weight: 800; color: #3b82f6;")
        sidebar_layout.addWidget(logo, 0, Qt.AlignCenter)
        
        logo_sub = QLabel("Your AI Study Companion", sidebar)
        logo_sub.setObjectName("SubHeaderLogo")
        sidebar_layout.addWidget(logo_sub, 0, Qt.AlignCenter)
        
        sidebar_layout.addSpacing(30)
        
        # Navigation Buttons
        self.btn_plan = QPushButton("Regenerate Plan", sidebar)
        self.btn_plan.setObjectName("PrimaryButton")
        self.btn_plan.clicked.connect(self.regenerate_plan)
        sidebar_layout.addWidget(self.btn_plan)
        
        self.btn_add_event = QPushButton("+ Add Event / Goal", sidebar)
        self.btn_add_event.clicked.connect(self.open_add_event_dialog)
        sidebar_layout.addWidget(self.btn_add_event)
        
        self.btn_stuck = QPushButton("⚠️ I'm Stuck!", sidebar)
        self.btn_stuck.setStyleSheet("background-color: #f59e0b; border-color: #d97706; color: #ffffff;")
        self.btn_stuck.clicked.connect(self.trigger_stuck_wizard)
        sidebar_layout.addWidget(self.btn_stuck)
        
        self.btn_distracted = QPushButton("🔄 I'm Distracted", sidebar)
        self.btn_distracted.setStyleSheet("background-color: #ef4444; border-color: #dc2626; color: #ffffff;")
        self.btn_distracted.clicked.connect(self.trigger_distraction_recovery)
        sidebar_layout.addWidget(self.btn_distracted)
        
        sidebar_layout.addStretch()
        
        self.btn_settings = QPushButton("⚙️ Settings", sidebar)
        self.btn_settings.clicked.connect(self.open_settings_dialog)
        sidebar_layout.addWidget(self.btn_settings)
        
        main_layout.addWidget(sidebar)
        
        # RIGHT COLUMN - Main Dashboard Grid & Commands
        right_panel = QVBoxLayout()
        right_panel.setSpacing(15)
        
        # Header Status Panel
        header = QHBoxLayout()
        user_name = self.config.get("user_name", "Buddy")
        self.lbl_welcome = QLabel(f"Hello, <b>{user_name}</b>! Let's make today productive.", self)
        self.lbl_welcome.setStyleSheet("font-size: 16px; color: #ffffff;")
        header.addWidget(self.lbl_welcome)
        
        header.addStretch()
        
        self.lbl_status = QLabel("Status: Idle", self)
        self.lbl_status.setStyleSheet("color: #a1a1aa; font-weight: bold; background-color: #1e1e24; padding: 5px 12px; border-radius: 12px;")
        header.addWidget(self.lbl_status)
        right_panel.addLayout(header)
        
        # Grid Dashboard Widgets
        grid = QGridLayout()
        grid.setSpacing(15)
        
        # Widget 1: Focus Timer Panel
        timer_panel = QFrame(self)
        timer_panel.setObjectName("DashboardPanel")
        timer_layout = QVBoxLayout(timer_panel)
        timer_layout.setContentsMargins(15, 15, 15, 15)
        
        lbl_timer_title = QLabel("Focus Timer", timer_panel)
        lbl_timer_title.setObjectName("PanelTitle")
        timer_layout.addWidget(lbl_timer_title)
        
        self.lbl_current_task = QLabel("Current Task: None", timer_panel)
        self.lbl_current_task.setStyleSheet("color: #94a3b8; font-size: 13px; font-weight: 600;")
        timer_layout.addWidget(self.lbl_current_task)
        
        self.lbl_timer_time = QLabel("25:00", timer_panel)
        self.lbl_timer_time.setObjectName("TimerLabel")
        self.lbl_timer_time.setAlignment(Qt.AlignCenter)
        timer_layout.addWidget(self.lbl_timer_time)
        
        self.timer_progress = QProgressBar(timer_panel)
        self.timer_progress.setValue(0)
        self.timer_progress.setFixedHeight(8)
        timer_layout.addWidget(self.timer_progress)
        
        timer_btns = QHBoxLayout()
        self.btn_timer_start = QPushButton("Start Focus", timer_panel)
        self.btn_timer_start.setObjectName("PrimaryButton")
        self.btn_timer_start.clicked.connect(self.timer_start_clicked)
        
        self.btn_timer_pause = QPushButton("Pause", timer_panel)
        self.btn_timer_pause.clicked.connect(self.timer_pause_clicked)
        
        self.btn_timer_reset = QPushButton("Reset", timer_panel)
        self.btn_timer_reset.clicked.connect(self.timer_reset_clicked)
        
        timer_btns.addWidget(self.btn_timer_start)
        timer_btns.addWidget(self.btn_timer_pause)
        timer_btns.addWidget(self.btn_timer_reset)
        timer_layout.addLayout(timer_btns)
        
        grid.addWidget(timer_panel, 0, 0)
        
        # Widget 2: Today's Schedule Panel (Interactive Checklist)
        schedule_panel = QFrame(self)
        schedule_panel.setObjectName("DashboardPanel")
        schedule_layout = QVBoxLayout(schedule_panel)
        schedule_layout.setContentsMargins(15, 15, 15, 15)
        
        lbl_sched_title = QLabel("Today's Schedule", schedule_panel)
        lbl_sched_title.setObjectName("PanelTitle")
        schedule_layout.addWidget(lbl_sched_title)
        
        self.schedule_list = QListWidget(schedule_panel)
        schedule_layout.addWidget(self.schedule_list)
        
        grid.addWidget(schedule_panel, 0, 1)
        
        # Widget 3: Upcoming Deadlines & Countdowns
        events_panel = QFrame(self)
        events_panel.setObjectName("DashboardPanel")
        events_layout = QVBoxLayout(events_panel)
        events_layout.setContentsMargins(15, 15, 15, 15)
        
        lbl_events_title = QLabel("Upcoming Exams / Deadlines", events_panel)
        lbl_events_title.setObjectName("PanelTitle")
        events_layout.addWidget(lbl_events_title)
        
        self.events_list = QListWidget(events_panel)
        events_layout.addWidget(self.events_list)
        
        grid.addWidget(events_panel, 1, 0)
        
        # Widget 4: Progress Stats Panel
        stats_panel = QFrame(self)
        stats_panel.setObjectName("DashboardPanel")
        stats_layout = QVBoxLayout(stats_panel)
        stats_layout.setContentsMargins(15, 15, 15, 15)
        
        lbl_stats_title = QLabel("Today's Progress", stats_panel)
        lbl_stats_title.setObjectName("PanelTitle")
        stats_layout.addWidget(lbl_stats_title)
        
        self.lbl_focus_stat = QLabel("⏱️ Total Focus Time: 0 min", stats_panel)
        self.lbl_focus_stat.setStyleSheet("font-size: 14px; font-weight: 500;")
        stats_layout.addWidget(self.lbl_focus_stat)
        
        self.lbl_tasks_stat = QLabel("✅ Completed Tasks: 0/0", stats_panel)
        self.lbl_tasks_stat.setStyleSheet("font-size: 14px; font-weight: 500;")
        stats_layout.addWidget(self.lbl_tasks_stat)
        
        self.lbl_distract_stat = QLabel("🚫 Distractions Logged: 0 events", stats_panel)
        self.lbl_distract_stat.setStyleSheet("font-size: 14px; font-weight: 500;")
        stats_layout.addWidget(self.lbl_distract_stat)
        
        stats_layout.addStretch()
        grid.addWidget(stats_panel, 1, 1)
        
        right_panel.addLayout(grid)
        
        # BOTTOM: Voice / Text Command Bar
        cmd_panel = QFrame(self)
        cmd_panel.setObjectName("DashboardPanel")
        cmd_layout = QHBoxLayout(cmd_panel)
        cmd_layout.setContentsMargins(10, 10, 10, 10)
        
        # Speech button
        self.btn_mic = QPushButton("🎙️ Voice", cmd_panel)
        self.btn_mic.setObjectName("VoiceButton")
        self.btn_mic.setStyleSheet("background-color: #10b981; border-color: #059669; padding: 10px; color: white;")
        self.btn_mic.clicked.connect(self.mic_clicked)
        cmd_layout.addWidget(self.btn_mic)
        
        # Command Text Input
        self.cmd_input = QLineEdit(cmd_panel)
        self.cmd_input.setPlaceholderText("Type command (e.g. 'start a 25 minute focus session', 'what's next?') and press Enter...")
        self.cmd_input.returnPressed.connect(self.submit_text_command)
        cmd_layout.addWidget(self.cmd_input)
        
        # Execute button
        self.btn_execute_cmd = QPushButton("Run", cmd_panel)
        self.btn_execute_cmd.clicked.connect(self.submit_text_command)
        cmd_layout.addWidget(self.btn_execute_cmd)
        
        right_panel.addWidget(cmd_panel)
        
        # Output Log Box
        self.lbl_response = QLabel("Ready.", self)
        self.lbl_response.setStyleSheet("color: #3b82f6; font-weight: 600; padding-left: 10px;")
        right_panel.addWidget(self.lbl_response)

        # Assistant Activity Log Box
        self.activity_log = QListWidget(self)
        self.activity_log.setObjectName("ActivityLog")
        self.activity_log.setFixedHeight(120)
        self.activity_log.setStyleSheet("background-color: #1a1a1e; border: 1px solid #2e2e38; border-radius: 8px; font-size: 11px; color: #a1a1aa;")
        right_panel.addWidget(self.activity_log)
        
        main_layout.addLayout(right_panel)

    def init_tray(self):
        """Sets up Windows system tray icon and menu."""
        self.tray = QSystemTrayIcon(self)
        
        # Try loading an icon from assets, or use a default standard style icon
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "assets", "tray_icon.png")
        if os.path.exists(icon_path):
            self.tray.setIcon(QIcon(icon_path))
        else:
            self.tray.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
            
        tray_menu = QMenu()
        
        action_open = QAction("Open FocusBuddy", self)
        action_open.triggered.connect(self.showNormal)
        tray_menu.addAction(action_open)
        
        action_focus = QAction("Start Focus (25m)", self)
        action_focus.triggered.connect(lambda: self.timer.start_focus(25))
        tray_menu.addAction(action_focus)
        
        action_next = QAction("What's Next?", self)
        action_next.triggered.connect(lambda: self.execute_text_command("what's next"))
        tray_menu.addAction(action_next)
        
        action_progress = QAction("Today's Progress", self)
        action_progress.triggered.connect(lambda: self.execute_text_command("how am i doing today"))
        tray_menu.addAction(action_progress)
        
        tray_menu.addSeparator()
        
        action_settings = QAction("Settings", self)
        action_settings.triggered.connect(self.open_settings_dialog)
        tray_menu.addAction(action_settings)
        
        action_exit = QAction("Exit", self)
        action_exit.triggered.connect(self.exit_app)
        tray_menu.addAction(action_exit)
        
        self.tray.setContextMenu(tray_menu)
        self.tray.show()
        
        # Tray click handler
        self.tray.activated.connect(self.tray_activated)

    def tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.showNormal()
                self.activateWindow()

    def connect_signals(self):
        # Assistant Engine Signals
        self.assistant.state_changed.connect(self.update_assistant_state)
        self.assistant.gui_status_changed.connect(self.update_gui_status)
        self.assistant.log_added.connect(self.add_activity_log)
        self.assistant.timer_updated.connect(self.update_timer_display)
        self.assistant.countdowns_updated.connect(self.refresh_countdowns)
        self.assistant.response_emitted.connect(self.handle_assistant_response)
        self.assistant.schedule_updated.connect(self.refresh_dashboard)
        self.assistant.stuck_wizard_triggered.connect(self.trigger_stuck_wizard)
        
        # Scheduler distraction warnings can still be listened to directly for dialogs
        self.scheduler.distraction_detected.connect(self.distraction_warning)

    # --- BUTTON TRIGGERS ---
    def timer_start_clicked(self):
        # Pick currently selected task if any
        selected_item = self.schedule_list.currentItem()
        task_id = None
        task_name = "Java Coding" # Default task
        
        if selected_item:
            # Try to get task ID stored in item data
            task_id = selected_item.data(Qt.UserRole)
            task_name = selected_item.text().split(" - ")[-1]
            
        focus_duration = int(self.config.get("focus_duration", 25))
        self.timer.start_focus(focus_duration, task_id)
        self.lbl_current_task.setText(f"Current Task: {task_name}")

    def timer_pause_clicked(self):
        if self.timer.current_state == "Paused":
            self.timer.resume()
            self.btn_timer_pause.setText("Pause")
        else:
            self.timer.pause()
            self.btn_timer_pause.setText("Resume")

    def timer_reset_clicked(self):
        self.timer.stop()
        self.btn_timer_pause.setText("Pause")
        self.lbl_current_task.setText("Current Task: None")
        self.refresh_dashboard()

    def mic_clicked(self):
        self.assistant.trigger_voice_input()

    def update_assistant_state(self, state):
        pass

    def update_gui_status(self, status):
        self.lbl_status.setText(f"Assistant: {status}")
        
        # Color code status label
        colors = {
            "Ready": "color: #a1a1aa; background-color: #1e1e24;",
            "Listening": "color: #ffffff; background-color: #ef4444;",
            "Thinking": "color: #ffffff; background-color: #3b82f6;",
            "Speaking": "color: #ffffff; background-color: #10b981;",
            "Focus Active": "color: #ffffff; background-color: #1d4ed8;",
            "In Conversation": "color: #ffffff; background-color: #d97706;"
        }
        self.lbl_status.setStyleSheet(colors.get(status, colors["Ready"]) + " padding: 5px 12px; border-radius: 12px; font-weight: bold;")
        
        # Visual mic state
        if status == "Listening":
            self.btn_mic.setStyleSheet("background-color: #ef4444; border-color: #dc2626; padding: 10px; color: white; font-weight: bold;")
        elif status == "In Conversation":
            self.btn_mic.setStyleSheet("background-color: #d97706; border-color: #b45309; padding: 10px; color: white; font-weight: bold;")
        else:
            self.btn_mic.setStyleSheet("background-color: #10b981; border-color: #059669; padding: 10px; color: white;")

    def add_activity_log(self, timestamp, message):
        item_text = f"{timestamp} — {message}"
        self.activity_log.addItem(item_text)
        self.activity_log.scrollToBottom()

    def handle_assistant_response(self, text):
        self.lbl_response.setText(text)

    def submit_text_command(self):
        text = self.cmd_input.text().strip()
        if text:
            self.cmd_input.clear()
            self.execute_text_command(text)

    def execute_text_command(self, text):
        self.assistant.add_log("User Input (Text)", f'"{text}"')
        self.assistant.gui_status_changed.emit("Thinking")
        response = self.router.route(text)
        self.assistant.gui_status_changed.emit("Speaking")
        if response == "__TRIGGER_STUCK_MODE__":
            self.assistant.add_log("Assistant", "Triggering Stuck Recovery Mode.")
            self.assistant.set_state("USER_STUCK")
            self.trigger_stuck_wizard()
            self.lbl_response.setText("Stuck mode opened.")
        else:
            self.assistant.add_log("Assistant", response)
            self.lbl_response.setText(response)
        self.refresh_dashboard()
        self.assistant.gui_status_changed.emit("Ready")

    # --- WIZARDS & DIALOGS ---
    def trigger_stuck_wizard(self):
        stuck_dialog = StuckWidget(self.ai, self.tts, self)
        stuck_dialog.exec()
        self.refresh_dashboard()

    def trigger_distraction_recovery(self):
        self.timer.start_recovery_session()
        self.lbl_current_task.setText("Current Task: Recovery Session")
        self.refresh_dashboard()

    def open_add_event_dialog(self):
        dlg = EventDialog(self.db, self.planner, self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh_dashboard()

    def open_settings_dialog(self):
        dlg = SettingsDialog(self.config, self.scheduler, self)
        if dlg.exec() == QDialog.Accepted:
            # Refresh user greeting details
            user_name = self.config.get("user_name", "Buddy")
            self.lbl_welcome.setText(f"Hello, <b>{user_name}</b>! Let's make today productive.")
            self.refresh_dashboard()

    def regenerate_plan(self):
        self.planner.generate_daily_schedule()
        self.refresh_dashboard()
        self.lbl_response.setText("Daily study plan updated.")
        self.tts.speak("I have updated your study plan for today.")

    # --- UI UPDATE SLOTS ---
    def update_timer_display(self, minutes, seconds, progress):
        self.lbl_timer_time.setText(f"{minutes:02d}:{seconds:02d}")
        self.timer_progress.setValue(int(progress * 100))

    def update_timer_state(self, state):
        self.lbl_status.setText(f"Status: {state}")
        # Color code status label
        colors = {
            "Idle": "color: #a1a1aa; background-color: #1e1e24;",
            "Focus": "color: #ffffff; background-color: #1d4ed8;",
            "Break": "color: #ffffff; background-color: #059669;",
            "Recovery": "color: #ffffff; background-color: #d97706;",
            "Paused": "color: #ffffff; background-color: #4b5563;"
        }
        self.lbl_status.setStyleSheet(colors.get(state, colors["Idle"]) + " padding: 5px 12px; border-radius: 12px; font-weight: bold;")

    def timer_session_completed(self, session_type, duration_minutes):
        # Refresh dashboard stats
        self.refresh_dashboard()
        
        # Trigger desktop alert notification
        self.notifier.send_notification(
            title="Session Complete!",
            message=f"Your {session_type} session of {duration_minutes} minutes has finished."
        )

    def distraction_warning(self, window_title):
        # Minimize distracting window or overlay window warning
        # Since overlay window is simple, show a warning messagebox that is non-judgmental
        # Cover screen option: we can pop up a critical reminder that stays on top.
        msg = QMessageBox(self)
        msg.setWindowTitle("Return to Focus")
        msg.setText(f"It looks like you opened a distracting app: '{window_title}'.")
        msg.setInformativeText("That is okay! Let's return to your task. Your focus timer is still running.")
        msg.setIcon(QMessageBox.Warning)
        msg.setStandardButtons(QMessageBox.Ok)
        
        # Bring FocusBuddy window to front
        self.showNormal()
        self.activateWindow()
        msg.exec()

    def handle_schedule_alert(self, task_name, start_time):
        self.notifier.send_notification(
            title="Schedule Alert",
            message=f"It is {start_time}. Time to start: {task_name}."
        )

    # --- DATA REFRESH ---
    def refresh_dashboard(self):
        # 1. Refresh today's checklist
        self.schedule_list.clear()
        today_str = datetime.now().strftime("%Y-%m-%d")
        schedule = self.db.get_schedule_for_date(today_str)
        
        completed_count = 0
        for item in schedule:
            list_item = QListWidgetItem()
            # Storing ID
            list_item.setData(Qt.UserRole, item['id'])
            
            # Checkbox layout
            chk_text = f"{item['start_time']} - {item['task_name']}"
            list_item.setText(chk_text)
            
            if item['status'] == 'Completed':
                list_item.setCheckState(Qt.Checked)
                completed_count += 1
            else:
                list_item.setCheckState(Qt.Unchecked)
                
            self.schedule_list.addItem(list_item)
            
        # Register checklist toggling trigger
        self.schedule_list.itemChanged.connect(self.schedule_item_checked)

        # 2. Refresh Upcoming events list with countdowns
        self.scheduler._update_countdowns()

        # 3. Refresh statistics
        # Completed tasks count
        total_tasks = len(schedule)
        self.lbl_tasks_stat.setText(f"✅ Completed Tasks: {completed_count}/{total_tasks}")
        
        # Focus minutes
        sessions = self.db.get_focus_sessions(limit=100)
        focus_time = 0
        for s in sessions:
            if s['timestamp'].startswith(today_str) and s['type'] in ['focus', 'recovery']:
                focus_time += s['completed_minutes']
        self.lbl_focus_stat.setText(f"⏱️ Total Focus Time: {focus_time} min")
        
        # Distractions
        distractions = self.db.get_distraction_count(start_date=today_str)
        self.lbl_distract_stat.setText(f"🚫 Distractions Logged: {distractions} events")

    def schedule_item_checked(self, item):
        # Disconnect signal temporarily to avoid recursion
        self.schedule_list.itemChanged.disconnect(self.schedule_item_checked)
        
        item_id = item.data(Qt.UserRole)
        is_checked = item.checkState() == Qt.Checked
        status = "Completed" if is_checked else "Pending"
        
        self.db.update_schedule_item_status(item_id, status)
        
        # Reconnect signal
        self.schedule_list.itemChanged.connect(self.schedule_item_checked)
        
        self.refresh_dashboard()

    def refresh_countdowns(self, countdown_list):
        self.events_list.clear()
        for ev in countdown_list:
            item = QListWidgetItem(f"{ev['type']}: {ev['name']} — {ev['countdown']} ({ev['date']})")
            # Apply priority colors
            colors = {"High": "#ef4444", "Medium": "#f59e0b", "Low": "#10b981"}
            item.setForeground(Qt.GlobalColor.white)
            self.events_list.addItem(item)

    # --- APP CONTROL & TRAY CLOSE ---
    def closeEvent(self, event):
        """Minimize to tray instead of exit when user closes main window."""
        if self.tray.isVisible():
            self.hide()
            self.tray.showMessage(
                "FocusBuddy AI",
                "FocusBuddy is still running in the system tray. Right-click to exit.",
                QSystemTrayIcon.Information,
                2000
            )
            event.ignore()
        else:
            event.accept()

    def exit_app(self):
        self.tray.hide()
        self.timer.stop()
        self.tts.stop()
        sys.exit(0)
