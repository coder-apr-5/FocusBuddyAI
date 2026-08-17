import os
import unittest
from app.ai.orchestrator import AIOrchestrator
from app.ai.provider import LocalProvider, GroqProvider

class MockFailedProvider:
    def get_response(self, prompt, context_json=None):
        raise ConnectionError("Mock network failure")
    def get_stuck_response(self, stage, user_input):
        raise ConnectionError("Mock stuck failure")

class TestAIOrchestrator(unittest.TestCase):
    def test_fallback_sequence(self):
        # Create orchestrator with no keys (should fall back to local rule-based directly)
        orchestrator = AIOrchestrator()
        
        # Verify provider configuration
        self.assertIsNone(orchestrator.groq_provider)
        self.assertIsNone(orchestrator.gemini_provider)
        self.assertIsNone(orchestrator.openrouter_provider)
        
        response = orchestrator.get_response("hello")
        self.assertIn("greetings", response.lower() or "focusbuddy" in response.lower() or "support" in response.lower())

    def test_error_handling_fallback(self):
        # Configure orchestrator with a mock failed provider
        orchestrator = AIOrchestrator()
        orchestrator.groq_provider = MockFailedProvider() # Groq will throw error
        orchestrator.gemini_provider = None
        orchestrator.openrouter_provider = None
        
        # Should gracefully catch the Groq exception and query Local Provider
        response = orchestrator.get_response("hello")
        self.assertIn("support", response.lower())
        
        # Stuck Mode fallback
        stuck_response = orchestrator.get_stuck_response(0, "java compilation error")
        self.assertIn("debug", stuck_response.lower() or "problem" in stuck_response.lower())
