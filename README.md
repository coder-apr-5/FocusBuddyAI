# FocusBuddy AI 🚀

FocusBuddy AI is a universal, personal, offline-first voice-based focus, productivity, study-planning, and reminder assistant. Designed as a support-driven Windows desktop application, it helps you structure your study or work sessions, follow a dynamically updated schedule, calculate exam/deadline countdowns, and recover gracefully when you get stuck or lose focus.

---

## Features

1. **Dashboard & Focus Mode:** A modern dark-mode PySide6 desktop panel presenting:
   - Today's dynamic study checklist.
   - Upcoming deadlines and exams countdown.
   - Interactive focus timer (25 min focus + 5 min break, customizable).
   - Daily progress analytics.
2. **Local Voice Assistant:** Full support for local voice controls and announcements (via native offline Windows speech synthesis SAPI5 and speech recognition libraries) with typed command fallback.
3. **Distraction Recovery:**
   - Say `"I'm distracted"` to automatically launch a 10-minute non-judgmental recovery session.
   - Say `"I'm stuck"` to trigger the interactive Socratic Stuck Mode wizard, offering progressive clues instead of direct answers to build independent problem-solving skills.
4. **Active Window Monitor (Laptop-Friendly):** Configurable active window tracking. If you navigate to distracting websites/apps (e.g., YouTube, Reddit, Netflix) during a Focus Session, it alerts you and opens a return-to-focus prompt.
5. **Intelligent Planning Engine:** Periodically queries upcoming deadlines, topic difficulty, and distraction logs to generate a customized study plan tailored to your exam schedules and weak areas.
6. **Optional Cloud LLM (Gemini):** If configured with a Gemini API key, the assistant switches to conversational AI mode for explanations, study coaching, and natural interactions.

---

## Folder Layout

```
FocusBuddy/
├── app/
│   ├── core/           # Config manager, startup registry hooks, command router
│   ├── voice/          # local Speech-to-Text & Text-to-Speech wrappers
│   ├── scheduler/      # Window monitors & alert timers
│   ├── focus/          # Focus timer states & recovery sessions
│   ├── planner/        # Rule-based schedule planning engine
│   ├── ai/             # AI abstract layer: Rule-based & Gemini LLM
│   ├── database/       # SQLite persistent schema & operations
│   ├── notifications/  # Native desktop toast notification services
│   └── ui/             # PySide6 GUI views, styles, and setup wizards
├── data/               # Persistent database storage folder (focusbuddy.db)
├── tests/              # Unit test suite
├── requirements.txt    # Application dependencies
├── .env.example        # Environment template (Gemini API keys)
└── run.py              # Main bootstrapper
```

---

## Setup Instructions

### Prerequisites
- Windows 10/11
- Python 3.11 or later
- Active Microphone (for voice commands)

### Installation
1. Clone or copy the folder structure.
2. Open PowerShell in the project directory:
   ```powershell
   # Create virtual environment
   python -m venv .venv

   # Activate virtual environment
   .venv\Scripts\Activate.ps1

   # Install dependencies
   pip install -r requirements.txt
   ```

### Running the App
Launch the entry point from PowerShell:
```powershell
python run.py
```
*Note: On the first launch, the Setup Wizard dialog will open to capture your profile preferences.*

### Website Blocking Option
To enable hosts-file website blocking, run the application from an Administrator PowerShell prompt:
```powershell
# Start as Administrator
Start-Process python -ArgumentList "run.py" -Verb RunAs
```

---

## Voice & Text Commands

Try asking or typing these prompts in the bottom bar:
- *"What's next?"*
- *"What is my schedule today?"*
- *"Start a 25 minute focus session"*
- *"Start coding"*
- *"I'm distracted"* / *"I'm losing focus"*
- *"I'm stuck"*
- *"I have an exam on October 5"*
- *"Move my next task to 7 PM"*
- *"How am I doing today?"*

---

## Testing & Verification
Run the unit test suite:
```powershell
python -m unittest discover -s tests
```

---

## Standalone Executable Packaging
You can compile FocusBuddy AI into a single Windows `.exe` using PyInstaller:
```powershell
# Install pyinstaller
pip install pyinstaller

# Package into standalone exe
pyinstaller --noconsole --onefile --name="FocusBuddy" run.py
```
The compiled binary will be placed inside the `dist/` directory.
