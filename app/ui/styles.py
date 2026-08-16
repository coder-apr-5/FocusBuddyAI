# QSS (Qt Style Sheet) for FocusBuddy AI (Modern Slate Dark Theme)

MODERN_DARK_STYLESHEET = """
/* Global Styles */
QMainWindow {
    background-color: #0f0f11;
}

QWidget {
    color: #e2e8f0;
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 13px;
}

/* Sidebar / Navigation Bar */
QFrame#Sidebar {
    background-color: #16161a;
    border-right: 1px solid #27272a;
}

/* Main Dashboard Panels */
QFrame#DashboardPanel {
    background-color: #1e1e24;
    border: 1px solid #2e2e38;
    border-radius: 16px;
}

/* Labels */
QLabel#PanelTitle {
    font-size: 18px;
    font-weight: bold;
    color: #ffffff;
}

QLabel#HeaderLogo {
    font-size: 20px;
    font-weight: 800;
    color: #3b82f6; /* Accent Blue */
}

QLabel#SubHeaderLogo {
    font-size: 11px;
    color: #71717a;
    font-weight: 600;
}

/* Push Buttons - Primary */
QPushButton {
    background-color: #27272a;
    border: 1px solid #3f3f46;
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 600;
    color: #e2e8f0;
}

QPushButton:hover {
    background-color: #3f3f46;
    border-color: #52525b;
}

QPushButton:pressed {
    background-color: #18181b;
}

QPushButton#PrimaryButton {
    background-color: #3b82f6;
    border: 1px solid #2563eb;
    color: #ffffff;
}

QPushButton#PrimaryButton:hover {
    background-color: #2563eb;
    border-color: #1d4ed8;
}

QPushButton#PrimaryButton:pressed {
    background-color: #1d4ed8;
}

QPushButton#DangerButton {
    background-color: #ef4444;
    border: 1px solid #dc2626;
    color: #ffffff;
}

QPushButton#DangerButton:hover {
    background-color: #dc2626;
    border-color: #b91c1c;
}

QPushButton#VoiceButton {
    background-color: #10b981;
    border: 1px solid #059669;
    border-radius: 20px; /* Circular button */
    padding: 10px;
    min-width: 40px;
    min-height: 40px;
}

QPushButton#VoiceButton:hover {
    background-color: #059669;
}

QPushButton#VoiceButton:checked {
    background-color: #ef4444;
    border-color: #dc2626;
}

/* Text Inputs / LineEdits / ComboBoxes */
QLineEdit, QTextEdit, QTimeEdit, QDateEdit, QComboBox, QSpinBox {
    background-color: #18181b;
    border: 1px solid #27272a;
    border-radius: 6px;
    padding: 6px 10px;
    color: #f4f4f5;
}

QLineEdit:focus, QTextEdit:focus, QTimeEdit:focus, QDateEdit:focus, QComboBox:focus, QSpinBox:focus {
    border: 1px solid #3b82f6;
    background-color: #1b1b22;
}

/* List Widgets */
QListWidget {
    background-color: transparent;
    border: none;
}

QListWidget::item {
    background-color: #1e1e24;
    border: 1px solid #27272a;
    border-radius: 10px;
    padding: 10px;
    margin-bottom: 8px;
    color: #e2e8f0;
}

QListWidget::item:hover {
    background-color: #27272a;
    border-color: #3b82f6;
}

QListWidget::item:selected {
    background-color: #27272a;
    border: 1px solid #3b82f6;
    color: #ffffff;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background-color: #16161a;
    width: 8px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background-color: #3f3f46;
    min-height: 20px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background-color: #52525b;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
}

/* Timer Display text */
QLabel#TimerLabel {
    font-size: 54px;
    font-weight: 800;
    color: #ffffff;
    font-family: "Courier New", monospace;
}

/* Checkboxes */
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 1px solid #27272a;
    border-radius: 4px;
    background-color: #18181b;
}

QCheckBox::indicator:checked {
    background-color: #3b82f6;
    image: url(check_icon.png); /* Fallback to standard check drawing if no image */
}

/* Progress Bar */
QProgressBar {
    border: 1px solid #27272a;
    border-radius: 6px;
    text-align: center;
    background-color: #18181b;
}

QProgressBar::chunk {
    background-color: #3b82f6;
    border-radius: 5px;
}
"""
