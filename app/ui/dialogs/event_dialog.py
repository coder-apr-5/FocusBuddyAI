from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QDateEdit, QTimeEdit, QPushButton, QTextEdit, QFormLayout
from PySide6.QtCore import QDate, QTime, Qt
from datetime import datetime

class EventDialog(QDialog):
    def __init__(self, db_manager, planner_engine, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.planner = planner_engine
        
        self.setWindowTitle("Add Important Event / Goal")
        self.setMinimumSize(400, 480)
        
        self.setObjectName("DashboardPanel")
        self.setStyleSheet("background-color: #16161a; color: #e2e8f0;")
        
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title_label = QLabel("Create New Event / Goal", self)
        title_label.setObjectName("PanelTitle")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #3b82f6;")
        layout.addWidget(title_label)
        
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        
        # Event Type
        self.type_combo = QComboBox(self)
        self.type_combo.addItems([
            "Exam", "Interview", "Coding Test", "Assignment", 
            "Project", "Deadline", "Job Application", "Personal Goal", "Study Topic"
        ])
        form_layout.addRow("Event Type:", self.type_combo)
        
        # Name
        self.name_input = QLineEdit(self)
        self.name_input.setPlaceholderText("e.g. TCS NQT, Semester DBMS Exam")
        form_layout.addRow("Name:", self.name_input)
        
        # Date
        self.date_input = QDateEdit(self)
        self.date_input.setCalendarPopup(True)
        self.date_input.setDate(QDate.currentDate().addDays(7))
        form_layout.addRow("Date:", self.date_input)
        
        # Time
        self.time_input = QTimeEdit(self)
        self.time_input.setTime(QTime(10, 0)) # Default 10:00 AM
        form_layout.addRow("Time (Optional):", self.time_input)
        
        # Priority
        self.priority_combo = QComboBox(self)
        self.priority_combo.addItems(["High", "Medium", "Low"])
        form_layout.addRow("Priority:", self.priority_combo)
        
        # Prep Topics
        self.topics_input = QLineEdit(self)
        self.topics_input.setPlaceholderText("e.g. Arrays, Trees, SQL Queries (comma separated)")
        form_layout.addRow("Prep Topics:", self.topics_input)
        
        # Target
        self.target_input = QLineEdit(self)
        self.target_input.setPlaceholderText("e.g. Score 90%, Get Offer Letter")
        form_layout.addRow("Target Goals:", self.target_input)
        
        # Description
        self.desc_input = QTextEdit(self)
        self.desc_input.setPlaceholderText("Add notes or details here...")
        self.desc_input.setMaximumHeight(80)
        form_layout.addRow("Description:", self.desc_input)
        
        layout.addLayout(form_layout)
        layout.addStretch()
        
        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_cancel = QPushButton("Cancel", self)
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_save = QPushButton("Add Event", self)
        self.btn_save.setObjectName("PrimaryButton")
        self.btn_save.clicked.connect(self.save_event)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout)

    def save_event(self):
        name = self.name_input.text().strip()
        if not name:
            self.name_input.setFocus()
            return
            
        type_ = self.type_combo.currentText()
        date_str = self.date_input.date().toString("yyyy-MM-dd")
        time_str = self.time_input.time().toString("HH:mm")
        priority = self.priority_combo.currentText()
        prep_topics = self.topics_input.text().strip()
        target = self.target_input.text().strip()
        desc = self.desc_input.toPlainText().strip()
        
        # Save to database
        self.db.add_event(
            name=name,
            type_=type_,
            date=date_str,
            time=time_str,
            priority=priority,
            description=desc,
            prep_topics=prep_topics,
            target=target
        )
        
        # Automatically update schedule to prioritize new topics
        self.planner.generate_daily_schedule()
        
        self.accept()
