import os
from app.ai.provider import LocalProvider, GroqProvider, GeminiProvider, OpenRouterProvider

class AIOrchestrator:
    def __init__(self, config_manager=None):
        self.config = config_manager
        
        # Load API keys from environment or database configuration
        self.groq_key = os.getenv("GROQ_API_KEY") or (self.config.get("groq_api_key", "") if self.config else "")
        self.gemini_key = os.getenv("GEMINI_API_KEY") or (self.config.get("gemini_api_key", "") if self.config else "")
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY") or (self.config.get("openrouter_api_key", "") if self.config else "")

        # Instantiate providers
        self.local_provider = LocalProvider()
        self.groq_provider = GroqProvider(self.groq_key) if self.groq_key else None
        self.gemini_provider = GeminiProvider(self.gemini_key) if self.gemini_key else None
        self.openrouter_provider = OpenRouterProvider(self.openrouter_key) if self.openrouter_key else None

    def refresh_keys(self):
        """Reloads keys from database to catch changes in the settings dialog."""
        if self.config:
            self.groq_key = os.getenv("GROQ_API_KEY") or self.config.get("groq_api_key", "")
            self.gemini_key = os.getenv("GEMINI_API_KEY") or self.config.get("gemini_api_key", "")
            self.openrouter_key = os.getenv("OPENROUTER_API_KEY") or self.config.get("openrouter_api_key", "")
            
            self.groq_provider = GroqProvider(self.groq_key) if self.groq_key else None
            self.gemini_provider = GeminiProvider(self.gemini_key) if self.gemini_key else None
            self.openrouter_provider = OpenRouterProvider(self.openrouter_key) if self.openrouter_key else None

    def requires_llm(self, prompt: str) -> bool:
        """Determines if a prompt requires an LLM call or can be handled locally."""
        # Defaults to True for Stage 5. Will implement Stage 6 local-first routing rules.
        return True

    def get_response(self, prompt: str, context_json: str = None) -> str:
        """
        Executes query on the fallback sequence chain:
        Groq -> Gemini -> OpenRouter -> Local Rule-based.
        """
        self.refresh_keys() # Catch settings updates
        
        # 1. Try Groq
        if self.groq_provider:
            try:
                print("[Orchestrator] Querying Groq...")
                return self.groq_provider.get_response(prompt, context_json)
            except Exception as e:
                print(f"[Orchestrator] Groq failed: {e}. Falling back to Gemini...")

        # 2. Try Gemini
        if self.gemini_provider:
            try:
                print("[Orchestrator] Querying Gemini...")
                return self.gemini_provider.get_response(prompt, context_json)
            except Exception as e:
                print(f"[Orchestrator] Gemini failed: {e}. Falling back to OpenRouter...")

        # 3. Try OpenRouter
        if self.openrouter_provider:
            try:
                print("[Orchestrator] Querying OpenRouter...")
                return self.openrouter_provider.get_response(prompt, context_json)
            except Exception as e:
                print(f"[Orchestrator] OpenRouter failed: {e}. Falling back to Local Rule-Based...")

        # 4. Local Rule-Based AI Fallback
        print("[Orchestrator] Querying Local Rule-Based Fallback...")
        return self.local_provider.get_response(prompt, context_json)

    def get_stuck_response(self, stage: int, user_input: str) -> str:
        """
        Executes stuck coaching query on the fallback sequence chain:
        Groq -> Gemini -> OpenRouter -> Local Rule-based.
        """
        self.refresh_keys()
        
        # 1. Try Groq
        if self.groq_provider:
            try:
                print("[Orchestrator] Stuck Mode: Querying Groq...")
                return self.groq_provider.get_stuck_response(stage, user_input)
            except Exception as e:
                print(f"[Orchestrator] Groq Stuck failed: {e}. Falling back to Gemini...")

        # 2. Try Gemini
        if self.gemini_provider:
            try:
                print("[Orchestrator] Stuck Mode: Querying Gemini...")
                return self.gemini_provider.get_stuck_response(stage, user_input)
            except Exception as e:
                print(f"[Orchestrator] Gemini Stuck failed: {e}. Falling back to OpenRouter...")

        # 3. Try OpenRouter
        if self.openrouter_provider:
            try:
                print("[Orchestrator] Stuck Mode: Querying OpenRouter...")
                return self.openrouter_provider.get_stuck_response(stage, user_input)
            except Exception as e:
                print(f"[Orchestrator] OpenRouter Stuck failed: {e}. Falling back to Local...")

        # 4. Local Stuck Dialog Heuristics
        print("[Orchestrator] Stuck Mode: Querying Local Heuristics...")
        return self.local_provider.get_stuck_response(stage, user_input)
