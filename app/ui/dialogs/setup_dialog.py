from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox, QCheckBox, QPushButton, QTextEdit
from PySide6.QtCore import Qt

class SetupDialog(QDialog):
    def __init__(self, config_manager, planner_engine, parent=None):
        super().__init__(parent)
        self.config = config_manager
        self.planner = planner_engine
        
        self.setWindowTitle("Welcome to FocusBuddy AI")
        self.setMinimumSize(450, 500)
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowTitleHint)
        
        # Apply dark mode style properties
        self.setObjectName("DashboardPanel")
        self.setStyleSheet("background-color: #16161a; color: #e2e8f0;")
        
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)
        
        # Header Title
        title_label = QLabel("Set Up Your FocusBuddy AI", self)
        title_label.setObjectName("PanelTitle")
        title_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #3b82f6;")
        layout.addWidget(title_label)
        
        intro_label = QLabel("Let's configure your personalized workspace environment. All settings can be changed later.", self)
        intro_label.setWordWrap(True)
        intro_label.setStyleSheet("color: #94a3b8; font-size: 13px;")
        layout.addWidget(intro_label)
        
        # Name Input
        name_label = QLabel("What is your name?", self)
        name_label.setStyleSheet("font-weight: 600;")
        self.name_input = QLineEdit(self)
        self.name_input.setPlaceholderText("Enter your name (e.g. John)")
        self.name_input.setText("Buddy")
        layout.addWidget(name_label)
        layout.addWidget(self.name_input)
        
        # Available Study Hours
        hours_layout = QHBoxLayout()
        hours_label = QLabel("Daily available study/work hours:", self)
        hours_label.setStyleSheet("font-weight: 600;")
        self.hours_input = QDoubleSpinBox(self)
        self.hours_input.setRange(0.5, 16.0)
        self.hours_input.setValue(4.0)
        self.hours_input.setSingleStep(0.5)
        self.hours_input.setSuffix(" hours")
        hours_layout.addWidget(hours_label)
        hours_layout.addWidget(self.hours_input)
        layout.addLayout(hours_layout)
        
        # Focus Duration
        focus_layout = QHBoxLayout()
        focus_label = QLabel("Preferred focus duration:", self)
        focus_label.setStyleSheet("font-weight: 600;")
        self.focus_input = QSpinBox(self)
        self.focus_input.setRange(5, 120)
        self.focus_input.setValue(25)
        self.focus_input.setSuffix(" minutes")
        focus_layout.addWidget(focus_label)
        focus_layout.addWidget(self.focus_input)
        layout.addLayout(focus_layout)
        
        # Reminder preference
        remind_label = QLabel("How would you like to receive reminders?", self)
        remind_label.setStyleSheet("font-weight: 600;")
        self.remind_combo = QComboBox(self)
        self.remind_combo.addItems(["Voice & Desktop", "Desktop Only", "None"])
        layout.addWidget(remind_label)
        layout.addWidget(self.remind_combo)
        
        # Voice Toggle
        self.voice_checkbox = QCheckBox("Enable voice assistant announcements and local voice commands", self)
        self.voice_checkbox.setChecked(True)
        layout.addWidget(self.voice_checkbox)
        
        # Distraction controls
        self.distract_checkbox = QCheckBox("Enable active window monitoring to detect distractions", self)
        self.distract_checkbox.setChecked(True)
        layout.addWidget(self.distract_checkbox)
        
        layout.addStretch()
        
        # Submit button
        self.btn_submit = QPushButton("Get Started", self)
        self.btn_submit.setObjectName("PrimaryButton")
        self.btn_submit.setStyleSheet("font-size: 15px; padding: 10px; font-weight: bold; background-color: #3b82f6;")
        self.btn_submit.clicked.connect(self.save_settings)
        layout.addWidget(self.btn_submit)

    def save_settings(self):
        # Save values to config manager
        self.config.set("user_name", self.name_input.text().strip() or "Buddy")
        self.config.set("study_hours", str(self.hours_input.value()))
        self.config.set("focus_duration", str(self.focus_input.value()))
        self.config.set("reminder_pref", self.remind_combo.currentText())
        self.config.set("voice_enabled", str(self.voice_checkbox.isChecked()))
        self.config.set("distraction_monitoring", str(self.distract_checkbox.isChecked()))
        self.config.set("first_launch", "False")
        
        # Generate initial daily plan
        self.planner.generate_daily_schedule()
        
        self.accept()
