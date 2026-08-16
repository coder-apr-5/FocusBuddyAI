import os
import sys
import winreg
from app.database.db import DatabaseManager

class ConfigManager:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.init_defaults()

    def init_defaults(self):
        # Default application settings
        defaults = {
            "user_name": "Buddy",
            "study_hours": "4.0",
            "focus_duration": "25",
            "break_duration": "5",
            "reminder_pref": "Voice & Desktop",
            "voice_enabled": "True",
            "always_listening": "False",
            "cloud_ai_enabled": "False",
            "gemini_api_key": "",
            "distraction_monitoring": "True",
            "website_blocking": "False",
            "distracting_websites": "youtube.com,reddit.com,facebook.com,twitter.com,netflix.com,instagram.com,tiktok.com,twitch.tv",
            "startup_enabled": "False",
            "first_launch": "True"
        }
        for key, val in defaults.items():
            if self.db.get_setting(key) is None:
                self.db.set_setting(key, val)

    def get(self, key, default=None):
        val = self.db.get_setting(key)
        if val is None:
            return default
        # Cast common types
        if val.lower() == "true":
            return True
        if val.lower() == "false":
            return False
        try:
            if "." in val:
                return float(val)
            return int(val)
        except ValueError:
            return val

    def set(self, key, value):
        self.db.set_setting(key, str(value))
        
        # Handle startup registry key automatically if that setting changes
        if key == "startup_enabled":
            self.set_windows_startup(bool(value))

    def set_windows_startup(self, enable: bool):
        """Register/unregister application to run at Windows startup."""
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "FocusBuddyAI"
        
        # Determine executable path
        if getattr(sys, 'frozen', False):
            # Running as packed .exe
            exe_path = sys.executable
        else:
            # Running as raw script
            script_path = os.path.abspath(sys.argv[0])
            # Path to pythonw.exe in virtualenv (to run without terminal popup)
            venv_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            pythonw_exe = os.path.join(venv_dir, ".venv", "Scripts", "pythonw.exe")
            if os.path.exists(pythonw_exe):
                exe_path = f'"{pythonw_exe}" "{script_path}"'
            else:
                exe_path = f'"{sys.executable}" "{script_path}"'

        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
            if enable:
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, exe_path)
            else:
                try:
                    winreg.DeleteValue(key, app_name)
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except Exception as e:
            print(f"Error modifying startup registry key: {e}")
