from datetime import datetime
from plyer import notification

class NotificationManager:
    def __init__(self, config_manager, tts_engine):
        self.config = config_manager
        self.tts = tts_engine

    def send_notification(self, title: str, message: str, force_voice: bool = False):
        """Sends desktop notification and TTS voice alerts based on settings and quiet hours."""
        if self._is_quiet_hours():
            print(f"[Notifier Quiet Hours] Suppressed: {title} - {message}")
            return

        pref = self.config.get("reminder_pref", "Voice & Desktop")
        if pref == "None":
            return

        # 1. Desktop Notification (if preferred is Voice & Desktop or Desktop Only)
        if pref in ["Voice & Desktop", "Desktop Only"]:
            try:
                notification.notify(
                    title=title,
                    message=message,
                    app_name="FocusBuddy AI",
                    timeout=5
                )
            except Exception as e:
                print(f"Failed to display desktop toast notification: {e}")

        # 2. Voice Alert (if Voice & Desktop or force_voice is True)
        if (pref == "Voice & Desktop" or force_voice) and self.config.get("voice_enabled", True):
            # If the title is different from message, speak title first or just speak the message
            self.tts.speak(message)

    def _is_quiet_hours(self) -> bool:
        """Checks if current time is within quiet hours (default: 10 PM - 7 AM)."""
        now = datetime.now().time()
        start_quiet = datetime.strptime("22:00", "%H:%M").time() # 10:00 PM
        end_quiet = datetime.strptime("07:00", "%H:%M").time()   # 07:00 AM
        
        if start_quiet > end_quiet:
            # Spans midnight
            return now >= start_quiet or now <= end_quiet
        else:
            return start_quiet <= now <= end_quiet
