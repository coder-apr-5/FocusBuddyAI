import queue
import threading
import pyttsx3

class TTSEngine:
    def __init__(self, config_manager=None):
        self.config = config_manager
        self.speech_queue = queue.Queue()
        self.active = True
        self.thread = None
        self.engine = None
        
        # Start background speaking thread
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def speak(self, text):
        """Queue text to be spoken by the TTS engine."""
        if self.config and not self.config.get("voice_enabled", True):
            print(f"[TTS Bypass] {text}")
            return
        
        print(f"[TTS Queue] {text}")
        self.speech_queue.put(text)

    def stop(self):
        """Stop speaking and shut down background thread."""
        self.active = False
        self.speech_queue.put(None) # Signal thread to stop
        if self.thread:
            self.thread.join(timeout=1.0)

    def _run(self):
        # Initialize pyttsx3 in the worker thread.
        # This is CRITICAL because pyttsx3 is not thread-safe.
        try:
            self.engine = pyttsx3.init()
            # Set speech rate and volume
            self.engine.setProperty("rate", 160)
            self.engine.setProperty("volume", 0.9)
            
            # Select a voice (try to find a female/supporting voice if possible)
            voices = self.engine.getProperty("voices")
            if voices:
                # Default to the first voice, or search for Zira (female Windows voice)
                selected_voice = voices[0].id
                for voice in voices:
                    if "zira" in voice.name.lower():
                        selected_voice = voice.id
                        break
                self.engine.setProperty("voice", selected_voice)
        except Exception as e:
            print(f"Failed to initialize local TTS engine: {e}")
            self.engine = None

        while self.active:
            try:
                text = self.speech_queue.get(timeout=0.5)
                if text is None:
                    break
                
                if self.engine and text:
                    print(f"[TTS Speaking] {text}")
                    # In pyttsx3, calling engine.say() and engine.runAndWait() works synchronously
                    # in this background thread.
                    self.engine.say(text)
                    self.engine.runAndWait()
                
                self.speech_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error speaking text: {e}")
                # Re-initialize engine if it crashes
                try:
                    self.engine = pyttsx3.init()
                except:
                    pass
