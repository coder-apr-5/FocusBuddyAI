import time
import speech_recognition as sr
from PySide6.QtCore import QThread, Signal

class WakeWordThread(QThread):
    wake_word_detected = Signal()

    def __init__(self, config_manager=None):
        super().__init__()
        self.config = config_manager
        self._running = True
        self._paused = False
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 350
        self.recognizer.pause_threshold = 0.5

    def run(self):
        print("[WakeWord] Background wake-word thread started.")
        while self._running:
            # Check config or pause status
            if self._paused or (self.config and not self.config.get("wake_word_enabled", True)) or (self.config and not self.config.get("voice_enabled", True)):
                time.sleep(1.0)
                continue

            try:
                # Open microphone inside loop block (uses default driver sample rate for complete robustness)
                with sr.Microphone() as source:
                    # Quick adjust for ambient noise
                    self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    # Quick listen with short timeout
                    audio = self.recognizer.listen(source, timeout=1.5, phrase_time_limit=2.5)

                if self._paused or not self._running:
                    continue

                try:
                    text = self.recognizer.recognize_google(audio).lower()
                    print(f"[WakeWord Heard] '{text}'")
                    if "focusbuddy" in text or "focus buddy" in text or ("focus" in text and "buddy" in text):
                        print("[WakeWord] MATCH DETECTED!")
                        self.wake_word_detected.emit()
                except sr.UnknownValueError:
                    pass # Silence
                except Exception as e:
                    print(f"[WakeWord Recognition error] {e}")
            except sr.WaitTimeoutError:
                # No speech detected within timeout
                pass
            except Exception as e:
                # Silently handle expected device busy or stream closed errors when standard STT is active
                err_msg = str(e).lower()
                if "stream closed" in err_msg or "device busy" in err_msg or "-9988" in err_msg or "9988" in err_msg:
                    time.sleep(1.5)
                else:
                    print(f"[WakeWord Mic warning] {e}")
                    time.sleep(1.0)

    def pause_listening(self):
        """Temporarily pauses mic capture to release exclusive control."""
        print("[WakeWord] Pausing wake-word listener.")
        self._paused = True

    def resume_listening(self):
        """Resumes background mic monitoring."""
        print("[WakeWord] Resuming wake-word listener.")
        self._paused = False

    def stop(self):
        """Stops the thread worker loop."""
        self._running = False
        self.wait()
