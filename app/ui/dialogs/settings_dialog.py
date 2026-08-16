from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox, QCheckBox, QPushButton, QFormLayout
from PySide6.QtCore import Qt

class SettingsDialog(QDialog):
    def __init__(self, config_manager, scheduler_manager, parent=None):
        super().__init__(parent)
        self.config = config_manager
        self.scheduler = scheduler_manager
        
        self.setWindowTitle("Settings - FocusBuddy AI")
        self.setMinimumSize(450, 480)
        
        self.setObjectName("DashboardPanel")
        self.setStyleSheet("background-color: #16161a; color: #e2e8f0;")
        
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title_label = QLabel("FocusBuddy Settings", self)
        title_label.setObjectName("PanelTitle")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #3b82f6;")
        layout.addWidget(title_label)
        
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        
        # User Name
        self.name_input = QLineEdit(self)
        self.name_input.setText(self.config.get("user_name", "Buddy"))
        form_layout.addRow("User Name:", self.name_input)
        
        # Available Study Hours
        self.hours_input = QDoubleSpinBox(self)
        self.hours_input.setRange(0.5, 16.0)
        self.hours_input.setSingleStep(0.5)
        self.hours_input.setValue(float(self.config.get("study_hours", 4.0)))
        form_layout.addRow("Daily Study Hours:", self.hours_input)
        
        # Focus Duration
        self.focus_input = QSpinBox(self)
        self.focus_input.setRange(5, 120)
        self.focus_input.setValue(int(self.config.get("focus_duration", 25)))
        form_layout.addRow("Focus Duration (min):", self.focus_input)
        
        # Break Duration
        self.break_input = QSpinBox(self)
        self.break_input.setRange(1, 60)
        self.break_input.setValue(int(self.config.get("break_duration", 5)))
        form_layout.addRow("Break Duration (min):", self.break_input)
        
        # Reminders dropdown
        self.remind_combo = QComboBox(self)
        self.remind_combo.addItems(["Voice & Desktop", "Desktop Only", "None"])
        self.remind_combo.setCurrentText(self.config.get("reminder_pref", "Voice & Desktop"))
        form_layout.addRow("Reminder Type:", self.remind_combo)
        
        # Distraction Keywords
        self.distract_input = QLineEdit(self)
        self.distract_input.setText(self.config.get("distracting_websites", ""))
        self.distract_input.setToolTip("Comma-separated list of keywords/domains to monitor (e.g. youtube.com,facebook.com)")
        form_layout.addRow("Distracting Sites:", self.distract_input)
        
        # Gemini API Key
        self.gemini_key_input = QLineEdit(self)
        self.gemini_key_input.setEchoMode(QLineEdit.Password)
        self.gemini_key_input.setText(self.config.get("gemini_api_key", ""))
        form_layout.addRow("Gemini API Key:", self.gemini_key_input)
        
        layout.addLayout(form_layout)
        
        # Toggles
        self.voice_chk = QCheckBox("Voice Speech Enabled", self)
        self.voice_chk.setChecked(bool(self.config.get("voice_enabled", True)))
        layout.addWidget(self.voice_chk)
        
        self.monitor_chk = QCheckBox("Enable Active Window Monitoring", self)
        self.monitor_chk.setChecked(bool(self.config.get("distraction_monitoring", True)))
        layout.addWidget(self.monitor_chk)
        
        self.blocking_chk = QCheckBox("Block Distracting Websites (Requires Run as Admin)", self)
        self.blocking_chk.setChecked(bool(self.config.get("website_blocking", False)))
        layout.addWidget(self.blocking_chk)
        
        self.startup_chk = QCheckBox("Start FocusBuddy on Windows Boot", self)
        self.startup_chk.setChecked(bool(self.config.get("startup_enabled", False)))
        layout.addWidget(self.startup_chk)
        
        layout.addStretch()
        
        # Action Buttons
        btn_layout = QHBoxLayout()
        self.btn_cancel = QPushButton("Cancel", self)
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_save = QPushButton("Save Settings", self)
        self.btn_save.setObjectName("PrimaryButton")
        self.btn_save.clicked.connect(self.save_settings)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout)

    def save_settings(self):
        # Save to DB / config manager
        self.config.set("user_name", self.name_input.text().strip())
        self.config.set("study_hours", str(self.hours_input.value()))
        self.config.set("focus_duration", str(self.focus_input.value()))
        self.config.set("break_duration", str(self.break_input.value()))
        self.config.set("reminder_pref", self.remind_combo.currentText())
        self.config.set("distracting_websites", self.distract_input.text().strip())
        self.config.set("gemini_api_key", self.gemini_key_input.text().strip())
        
        # Settings triggers (calls logic behind toggles)
        self.config.set("voice_enabled", str(self.voice_chk.isChecked()))
        self.config.set("distraction_monitoring", str(self.monitor_chk.isChecked()))
        self.config.set("website_blocking", str(self.blocking_chk.isChecked()))
        self.config.set("startup_enabled", str(self.startup_chk.isChecked()))
        
        # Apply hosts block adjustments if enabled
        if self.blocking_chk.isChecked():
            self.scheduler.apply_website_blocking()
        else:
            self.scheduler.remove_website_blocking()
            
        self.accept()
