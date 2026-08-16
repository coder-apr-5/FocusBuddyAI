# pyrefly: ignore [missing-import]
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextBrowser, QProgressBar
# pyrefly: ignore [missing-import]
from PySide6.QtCore import Qt

class StuckWidget(QDialog):
    def __init__(self, ai_provider, tts_engine, parent=None):
        super().__init__(parent)
        self.ai = ai_provider
        self.tts = tts_engine
        
        self.setWindowTitle("Stuck Recovery Mode")
        self.setMinimumSize(500, 450)
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowTitleHint)
        
        self.setObjectName("DashboardPanel")
        self.setStyleSheet("background-color: #16161a; color: #e2e8f0;")
        
        # State machine
        self.current_stage = 0
        self.stage_names = [
            "Decompose Problem",
            "Identify Inputs/Outputs",
            "Solve Manually First",
            "Conceptual Hint",
            "Structural Pseudocode",
            "Full Walkthrough"
        ]
        
        self.init_ui()
        self.display_current_prompt("")

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header_layout = QHBoxLayout()
        title_label = QLabel("FocusBuddy Stuck Helper", self)
        title_label.setObjectName("PanelTitle")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #f59e0b;") # Warm orange/yellow alert
        header_layout.addWidget(title_label)
        
        self.lbl_stage = QLabel("Stage 1/6: Decompose Problem", self)
        self.lbl_stage.setStyleSheet("color: #a1a1aa; font-weight: 600;")
        header_layout.addWidget(self.lbl_stage, 0, Qt.AlignmentFlag.AlignRight)
        layout.addLayout(header_layout)
        
        # Progress Bar
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 6)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #f59e0b; }")
        layout.addWidget(self.progress_bar)
        
        # Conversation Display Box
        self.chat_display = QTextBrowser(self)
        self.chat_display.setStyleSheet("background-color: #1e1e24; border: 1px solid #2e2e38; border-radius: 8px; padding: 10px; font-size: 13px;")
        layout.addWidget(self.chat_display)
        
        # User input box
        input_layout = QHBoxLayout()
        self.txt_input = QLineEdit(self)
        self.txt_input.setPlaceholderText("Type your response here...")
        self.txt_input.returnPressed.connect(self.submit_response)
        
        self.btn_submit = QPushButton("Submit", self)
        self.btn_submit.setObjectName("PrimaryButton")
        self.btn_submit.setStyleSheet("background-color: #f59e0b; border-color: #d97706;")
        self.btn_submit.clicked.connect(self.submit_response)
        
        input_layout.addWidget(self.txt_input)
        input_layout.addWidget(self.btn_submit)
        layout.addLayout(input_layout)
        
        # Controls row
        ctrl_layout = QHBoxLayout()
        self.btn_reset = QPushButton("Restart Wizard", self)
        self.btn_reset.clicked.connect(self.reset_wizard)
        
        self.btn_close = QPushButton("I'm Good Now / Close", self)
        self.btn_close.clicked.connect(self.accept)
        
        ctrl_layout.addWidget(self.btn_reset)
        ctrl_layout.addStretch()
        ctrl_layout.addWidget(self.btn_close)
        layout.addLayout(ctrl_layout)

    def display_current_prompt(self, user_input):
        """Fetches hint/guidance from the AI provider and displays/speaks it."""
        self.lbl_stage.setText(f"Stage {self.current_stage + 1}/6: {self.stage_names[self.current_stage]}")
        self.progress_bar.setValue(self.current_stage)
        
        # Get AI hint response
        ai_response = self.ai.get_stuck_response(self.current_stage, user_input)
        
        # Print AI response to chat
        self.chat_display.append(f"<font color='#f59e0b'><b>FocusBuddy:</b></font> {ai_response}<br>")
        self.tts.speak(ai_response)

    def submit_response(self):
        user_text = self.txt_input.text().strip()
        if not user_text and self.current_stage < 5:
            # Require text except for the final solution reveal
            return
            
        self.txt_input.clear()
        
        # Display user response in chat
        if user_text:
            self.chat_display.append(f"<font color='#e2e8f0'><b>You:</b></font> {user_text}<br>")
            
        # Move state machine forward
        if self.current_stage < 5:
            self.current_stage += 1
            self.display_current_prompt(user_text)
        else:
            # solution already shown, clicking submit accepts
            self.accept()

    def reset_wizard(self):
        self.current_stage = 0
        self.chat_display.clear()
        self.progress_bar.setValue(0)
        self.display_current_prompt("")
