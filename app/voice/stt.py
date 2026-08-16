import threading
import speech_recognition as sr

class STTEngine:
    def __init__(self, config_manager=None):
        self.config = config_manager
        self.recognizer = sr.Recognizer()
        # Adjust recognizer thresholds for better sensitivity
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 1.0

    def listen_and_transcribe(self, callback):
        """
        Record audio from microphone and transcribe in a background thread.
        Calls callback(text, success) when done.
        """
        if self.config and not self.config.get("voice_enabled", True):
            callback("Voice input is currently disabled.", False)
            return

        thread = threading.Thread(target=self._record_and_transcribe_worker, args=(callback,), daemon=True)
        thread.start()

    def _record_and_transcribe_worker(self, callback):
        try:
            with sr.Microphone() as source:
                print("[STT] Adjusting for ambient noise...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1.0)
                print("[STT] Listening...")
                audio = self.recognizer.listen(source, timeout=5.0, phrase_time_limit=8.0)
                print("[STT] Finished recording, transcribing...")
                
                # Use Google Speech Recognition as standard (requires internet, but is free and works out-of-the-box)
                try:
                    text = self.recognizer.recognize_google(audio)
                    print(f"[STT Recognized] {text}")
                    callback(text, True)
                except sr.UnknownValueError:
                    print("[STT] Could not understand audio")
                    callback("Sorry, I could not understand that. Could you please repeat?", False)
                except sr.RequestError as e:
                    print(f"[STT] Service request error: {e}")
                    callback("Speech recognition service is currently unavailable. Check your internet connection.", False)
        except OSError as e:
            # Handle no microphone found
            print(f"[STT] Microphone error: {e}")
            callback("No microphone found. Please connect one or type your command instead.", False)
        except Exception as e:
            print(f"[STT] Unexpected error during recording: {e}")
            callback(f"Voice recording error: {str(e)}", False)
