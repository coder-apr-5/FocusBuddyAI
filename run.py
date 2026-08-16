import sys
import os
from PySide6.QtWidgets import QApplication, QDialog

# Ensure workspace packages can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database.db import DatabaseManager
from app.core.config import ConfigManager
from app.voice.tts import TTSEngine
from app.focus.timer import FocusTimer
from app.planner.engine import PlannerEngine
from app.scheduler.manager import SchedulerManager
from app.notifications.notifier import NotificationManager
from app.ai.provider import RuleBasedProvider, LLMProvider
from app.core.commands import CommandRouter
from app.ui.main_window import MainWindow
from app.ui.dialogs.setup_dialog import SetupDialog

def main():
    # 1. Initialize PySide6 Application
    app = QApplication(sys.argv)
    app.setApplicationName("FocusBuddy AI")
    app.setQuitOnLastWindowClosed(False) # Allows running in tray even when window is hidden

    # 2. Boot Core Modules & Database
    db = DatabaseManager()
    config = ConfigManager(db)
    
    # 3. Boot Voice Modules
    tts = TTSEngine(config)
    
    # 4. Boot Logic Modules
    timer = FocusTimer(db, tts)
    planner = PlannerEngine(db, config)
    
    # 5. Boot Background Monitor
    scheduler = SchedulerManager(db, config, timer, tts)
    
    # 6. Boot Alert System
    notifier = NotificationManager(config, tts)
    
    # 7. Boot AI Provider (LLM if configured, otherwise Rule-Based)
    rule_ai = RuleBasedProvider()
    api_key = config.get("gemini_api_key", "")
    
    if api_key:
        ai_provider = LLMProvider(api_key, rule_ai)
    else:
        ai_provider = rule_ai
        
    # 8. Boot Command Router
    router = CommandRouter(db, timer, planner, tts, ai_provider)
    
    # 9. First Launch check
    if config.get("first_launch", True):
        # Open first launch wizard dialog
        wizard = SetupDialog(config, planner)
        if wizard.exec() != QDialog.DialogCode.Accepted:
            # Quit if user cancels setup
            tts.stop()
            sys.exit(0)
            
    # 10. Start website blocking if enabled
    if config.get("website_blocking", False):
        scheduler.apply_website_blocking()

    # 11. Create & Show Dashboard Main Window
    main_window = MainWindow(db, config, timer, scheduler, tts, notifier, router, ai_provider)
    main_window.show()

    # 12. Run Qt Event Loop
    sys_exit_code = app.exec()
    
    # Clean shutdown of speech thread on exit
    tts.stop()
    sys.exit(sys_exit_code)

if __name__ == "__main__":
    main()
